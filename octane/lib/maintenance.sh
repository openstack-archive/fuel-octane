#!/bin/bash

export SVC_LIST="/root/services_list"
export SVC_LIST_TMP="${SVC_LIST}.tmp"

disable_apis() {
    $PSSH_RUN "grep -q 'backend maintenance' /etc/haproxy/haproxy.cfg || echo \
        'backend maintenance' >> /etc/haproxy/haproxy.cfg;
        sed -re 's%(stats socket /var/lib/haproxy/stats)%\1 level admin%' \
        -i /etc/haproxy/haproxy.cfg"
    $PSSH_RUN "for f in \$(grep -L 'mode *tcp' /etc/haproxy/conf.d/*); \
        do echo '  use_backend maintenance if TRUE' >> \$f; done"
    $PSSH_RUN "crm resource restart p_haproxy"
}

enable_apis() {
    $PSSH_RUN "sed -i '/use_backend maintenance if TRUE/d' \
        \$(grep -L 'mode *tcp' /etc/haproxy/conf.d/*)"
    $PSSH_RUN "pkill haproxy"
}

stop_corosync_services() {
    $PSSH_RUN "crm status | awk '/clone/ {print \$4}' \
        | tr -d [] | grep -vE '(mysql|haproxy|p_dns|p_ntp)' \
        | xargs -tI{} sh -c 'crm resource stop {}'"
}

stop_upstart_services() {
    local command=$(cat <<EOF
services="nova keystone heat neutron cinder glance"; \
echo -n \$services \
        | xargs -d" " -I{} sh -c 'ls /etc/init/{}* \
        | grep -Ev override \
        | sed -E "s,.*/([^\.]+)(\.conf|override)?$,\1," \
        | sort -u | xargs -I@ sh -c "status @ \
        | grep start/running >/dev/null 2>&1 && echo @"' \
        | tee $SVC_LIST_TMP;
    [ -f ${SVC_LIST} ] || mv ${SVC_LIST_TMP} ${SVC_LIST};
    for s in \$(cat ${SVC_LIST});
        do
            stop \$s;
        done
EOF
)
    $PSSH_RUN "$command"
}

stop_vip_resources() {
    $PSSH_RUN "echo vip__management vip__public \
        | xargs -I{} -d \  sh -c 'crm resource stop {}'"
}

start_vip_resources() {
    $PSSH_RUN "echo vip__management vip__public \
        | xargs -I{} -d \  sh -c 'crm resource stop {}'"
}

start_corosync_services() {
    $PSSH_RUN "pcs resource \
    | awk '/Clone Set:/ {print \$4; getline; print \$1}' \
    | sed 'N;s/\n/ /' | tr -d :[] \
    | grep Stopped | awk '{print \$1}' \
    | xargs -I@ sh -c \"crm resource start @\""
}

start_upstart_services() {
    local command=$(cat <<EOF
crm_services=\$(pcs resource \
    | awk '/Clone Set:/ {print \$4; getline; print \$1}' \
    | sed 'N;s/\n/ /' \
    | tr -d ':[]' | awk '{print substr(\$1,3)}');
for s in \$(<${SVC_LIST});
do
    for cs in \$crm_services; do
        if [ "\$cs" == "\$s" ]; then
            continue 2;
        fi;
    done;
    start \$s;
done;
EOF
)
    $PSSH_RUN "$command"
}

evacuate_neutron_agents() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -z "$(fuel node --node $1 | grep controller)" ] && \
        die "Node $1 is not a controller, exiting"
    local res
    local dst_node=$(list_nodes $(get_env_by_node $1) controller \
        | grep -v "node-$1" | head -1)
    local src_node=$(get_host_ip_by_node_id $1)
    for res in p_neutron-l3-agent p_neutron-dhcp-agent;
    do
        ssh root@$src_node "crm resource status $res \
            | grep node-$1 && pcs resource move $res $dst_node"
    done
}

mysql_maintenance_mode() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local cmd
    case "$2" in
        activate)
            cmd="disable server"
            ;;
        deactivate)
            cmd="enable server"
            ;;
        *)
            die "Use 'activate/deactivate' as a second argument"
            ;;
    esac
    for node in $(list_nodes $1 controller);
    do
        ssh root@$(get_host_ip_by_node_id ${node#node-}) \
            "echo '${cmd} mysqld/${node}' \
            | socat stdio /var/lib/haproxy/stats"
    done
}

cic_maintenance_mode() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    host_ip=$(get_host_ip_by_node_id $1)
    case "$2" in
        activate)
            ssh root@$host_ip "crm node maintenance"
            disable_wsrep $1
            ;;
        deactivate)
            enable_wsrep $1
            ssh root@$host_ip "crm node ready"
            ;;
    esac
}
