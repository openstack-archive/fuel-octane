#!/bin/sh
set -ex


if [ -z "$1" ]; then
        echo "Usage $0 <evacuation_host>"
        exit 2
fi

nova service-list --host $1

nova service-list | grep -q 'nova-compute.*enabled' && {
        nova service-disable $1 nova-compute
}

nova service-list | grep -q 'nova-compute.*enabled' || {
        echo "All nova-compute are disabled"
        exit 3
}

nova list --host $1 | grep ' ACTIVE ' | cut -d\| -f3 | sed -r 's/(^[ ]+?|[ ]+?$)//g' | xargs -tI% nova live-migration %
