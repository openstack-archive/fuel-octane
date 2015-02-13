#!/bin/sh -ex

container=`docker ps | awk '/cobbler/ {print $1}'`
docker restart $container
sleep 10
dockerctl copy ./pmanager.py cobbler:/usr/lib/python2.6/site-packages/cobbler/pmanager.py
dockerctl copy ./ubuntu_partition cobbler:/var/lib/cobbler/snippets/ubuntu_partition
dockerctl copy ./ubuntu_partition_late cobbler:/var/lib/cobbler/snippets/ubuntu_partition_late
