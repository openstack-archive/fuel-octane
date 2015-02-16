#!/bin/sh -ex

tmp=/tmp/update.sh.tmp

function copy() {
    local src=$1 dst=$2
    while true
    do
        dockerctl copy $dst $tmp
        cmp -s $src $tmp && break
        dockerctl copy $src $dst
        sleep 1
    done
}

container=`docker ps | awk '/cobbler/ {print $1}'`
docker restart $container
sleep 10
copy ./pmanager.py cobbler:/usr/lib/python2.6/site-packages/cobbler/pmanager.py
copy ./ubuntu_partition cobbler:/var/lib/cobbler/snippets/ubuntu_partition
copy ./ubuntu_partition_late cobbler:/var/lib/cobbler/snippets/ubuntu_partition_late
