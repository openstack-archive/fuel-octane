#!/bin/bash

export SVC_LIST="/root/services_list"
export SVC_LIST_TMP="${SVC_LIST}.tmp"

enable_apis() {
    $PSSH_RUN "sed -i '/use_backend maintenance if TRUE/d' \
        \$(grep -L 'mode *tcp' /etc/haproxy/conf.d/*)"
    $PSSH_RUN "pkill haproxy"
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
