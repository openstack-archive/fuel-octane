#!/bin/bash

set -x
set -e

main() {
    local src_node
    local dst_node
    [ -n "$1" ] || {
        echo "No source DB node"
        exit 1
    }
    src_node=$1
    [ -n "$2" ] || {
        echo "No destination DB node"
        exit 1
    }
    dst_node=$2
    dbs="keystone nova heat neutron glance cinder"
    dbs_tuple=$(echo $dbs | sed -re "s%^%'%;s% %', '%g;s%$%'%")
    ssh $src_node "mysqldump --add-drop-database --lock-all-tables --databases $dbs | gzip " \
    | tee dbs.original.sql.gz | ssh $dst_node "zcat | mysql"
    ssh $dst_node "keystone-manage db_sync;
nova-manage db sync;
heat-manage db_sync;
neutron-db-manage --config-file=/etc/neutron/neutron.conf upgrade head;
glance-manage db upgrade;
cinder-manage db sync"
}

get_ctrl() {
    [ -z "$1" ] && exit 1
    echo $(fuel node --env $1 | awk '/controller/ {print "node-" $1;exit}')
}

orig_ctrl=$(get_ctrl $1)
seed_ctrl=$(get_ctrl $2)
main $orig_ctrl $seed_ctrl
exit 0
