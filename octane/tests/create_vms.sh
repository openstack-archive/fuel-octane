#!/bin/bash

usage() {
    echo "Usage: $(basename $0) num_tenants num_server"
}

[ -z "$1" ] && {
    echo "$(usage)"
    exit 1
}

seq ${1:-3} | xargs -I{} keystone tenant-create --name test-{}
keystone tenant-list | awk -F\| '/test-/{print($2)}' | tr -d \ \
    | xargs -I@ neutron net-create --tenant-id @ test-net-@
keystone tenant-list | awk -F\| '/test-/{print($2)}' | tr -d \ \
    | xargs -I@ neutron subnet-create --tenant-id @ test-net-@ 192.168.111.0/24
for tenant in $(keystone tenant-list \
                | awk -F\| '/test-/{print($2)}' \
                | tr -d \ )
    do
        net=$(neutron net-show test-net-$tenant \
              | awk -F\| '/ id /{print($3)}' \
              | tr -d \ );
        image=$(nova image-list \
                | awk -F\| '/TestVM/'{print($2)} \
                | tr -d \ )
        flavor=$(nova flavor-list \
                 | awk -F\| '/m1.tiny/'{print($2)} \
                 | tr -d \ )
        seq ${2:-3} | xargs -tI@ nova --os-tenant-id=$tenant \
            boot \
            --flavor $flavor \
            --image $image \
            --nic net-id=$net test-server-$tenant-@
    done
