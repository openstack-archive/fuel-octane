#!/bin/sh
set -ex


if [ -z "$1" ]; then
        echo "Usage $0 <evacuation_host>"
        exit 2
fi

[ -f "/root/openrc" ] && . /root/openrc

nova service-list --host $1

[ `nova service-list | grep -c 'nova-compute.*enabled'` -gt 1 ] || {
        echo "You can't  disable last compute node"
        exit 3
}

nova service-list | grep -q 'nova-compute.*enabled' && {
        nova service-disable $1 nova-compute
}

while :; do
    VMS=$(nova list --host $1 | grep -i ' active ' | wc -l)
    if [ $VMS -ne 0 ]; then
        for VM in $(nova list --host $1 | grep ' ACTIVE ' \
                    | cut -d\| -f3 | sed -r 's/(^[ ]+?|[ ]+?$)//g'); do
            nova live-migration $VM
        done
    else
        VMS=$(nova list --host $1 | grep -i ' migrating ' | wc -l)
        if [ $VMS -ne 0 ]; then
            sleep 30
        else
            echo "All VMs migrated" && exit 0
        fi
    fi
done
