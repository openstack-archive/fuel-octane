#!/bin/bash

set -x

action=${1:-help}
version=${2:-icehouse}
hosts_file=${3:-controllers}
pssh_run="pssh -i -h $hosts_file"

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
        if [ \$cs -eq \$s ]; then
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
    command=$(cat <<EOF >> /etc/nova/nova.conf
[upgrade_levels]
compute=icehouse
conductor=icehouse
scheduler=icehouse
EOF
)
    $pssh_run "$command"
}

display_help_message() {
    echo "Usage: $0 COMMAND
COMMANDS:
    stop    - stop all openstack services on controller nodes
    start   - start all openstack services on controller nodes
    config VERSION  - update nova.conf with upgrade_levels configuration, VERSION
                      defines original version of OpenStack (defaults to
                      'icehouse')
    help    - show this message"
}

case $action in 
    stop)
        stop_corosync_services
        stop_upstart_services
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
