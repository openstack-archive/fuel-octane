#!/bin/bash

disable_apis() {
    $pssh_run "echo 'backend maintenance' >> /etc/haproxy.cfg"
    $pssh_run "for f in \$(grep -L 'mode *tcp' /etc/haproxy/conf.d/*); \
        do echo '  use_backend maintenance if TRUE' >> \$f; done"
    $pssh_run "pkill haproxy"
}

enable_apis() {
    $pssh_run "sed -i '/use_backend maintenance if TRUE/d' \
        \$(grep -L 'mode *tcp' /etc/haproxy/conf.d/*)"
    $pss_run "pkill haproxy"
}

stop_corosync_services() {
    $pssh_run "crm status | awk '/clone/ {print \$4}' \
        | tr -d [] | grep -vE '(mysql|haproxy)' \
        | xargs -tI{} sh -c 'crm resource stop {}'"
}

stop_upstart_services() {
    local command
    command=$(cat <<EOF
services="nova keystone heat neutron cinder glance"; \
echo -n \$services \
        | xargs -d" " -I{} sh -c 'ls /etc/init/{}* \
        | grep -Ev override \
        | sed -E "s,.*/([^\.]+)(\.conf|override)?$,\1," \
        | sort -u | xargs -I@ sh -c "status @ \
        | grep start/running >/dev/null 2>&1 && echo @"' \
        | tee services;
    for s in \$(cat services);
        do
            stop \$s;
        done
EOF
)
    $pssh_run "$command"
}

stop_vip_resources() {
    $pssh_run "echo vip__management vip__public \
        | xargs -I{} -d \  sh -c 'crm resource stop {}'"
}

start_vip_resources() {
    $pssh_run "echo vip__management vip__public \
        | xargs -I{} -d \  sh -c 'crm resource stop {}'"
}

start_corosync_services() {
    $pssh_run "pcs resource \
    | awk '/Clone Set:/ {print \$4; getline; print \$1}' \
    | sed 'N;s/\n/ /' | tr -d :[] \
    | grep Stopped | awk '{print \$1}' \
    | xargs -I@ sh -c \"crm resource start @\""
}

start_upstart_services() {
    local command
    command=$(cat <<EOF
crm_services=\$(pcs resource \
    | awk '/Clone Set:/ {print \$4; getline; print \$1}' \
    | sed 'N;s/\n/ /' \
    | tr -d ':[]' | awk '{print substr(\$1,3)}');
for s in \$(<services);
do
    for cs in \$crm_services; do
        if [ "\$cs" == "\$s" ]; then
            break 2;
        fi;
    done;
    start \$s;
done;
EOF
)
    $pssh_run "$command"
}

set_upgrade_levels() {
    local version
    local command
    version=${1:-icehouse}
    command="echo \"
[upgrade_levels]
compute=$version
conductor=$version
scheduler=$version\" >> /etc/nova/nova.conf"
    $pssh_run "$command"
}

display_help_message() {
    echo "Usage: $0 COMMAND ENV_ID [VERSION] [HOSTS]
COMMAND:
    disable     - disable API servers in environment via haproxy configuration
    enable      - enable API servers in environment via haproxy configuration
    stop        - stop all openstack services on controller nodes
    start       - start all openstack services on controller nodes
    stop_vips   - shutdown Virtual IP corosync resources on CIC nodes
    start_vips  - restore Virtual IP corosync resoucres on CIC nodes
    config VERSION  - update nova.conf with upgrade_levels configuration, VERSION
                      defines original version of OpenStack (defaults to
                      'icehouse')
    help        - show this message

ENV_ID      identifier of env in Fuel
VERSION     version of OpenStack Compute RPC
HOSTS       a name of file with list of CIC nodes, overrides ENV_ID"
}

set -x

action=${1:-help}
test -z "$2" && {
    display_help_message
    exit 1
}
env_id=${2}
version=${3:-icehouse}
hosts_file=${4}
test -z "$hosts_file" && {
    fuel node --env $env_id \
        | awk '/controller/ {print "node-" $1}' \
        > /tmp/controllers
    hosts_file=/tmp/controllers
}
pssh_run="pssh -i -h $hosts_file"

case $action in 
    disable)
        disable_apis
        ;;
    enable)
        enable_apis
        ;;
    stop)
        stop_corosync_services
        stop_upstart_services
        ;;
    stop_vips)
        stop_vip_resources
        ;;
    start_vips)
        start_vip_resources
        ;;
    config)
        set_upgrade_levels $version
        ;;
    start)
        start_corosync_services
        start_upstart_services
        ;;
    help)
        display_help_message
        ;;
    *)
        display_help_message
        ;;
esac
