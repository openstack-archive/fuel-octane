#!/bin/bash -ex

NODE=node-$1

while true; do
    echo .
    sleep 1
    dockerctl shell cobbler cobbler system report --name $NODE > /dev/null || continue
    dockerctl shell cobbler cobbler system edit --name $NODE --in-place --ksmeta="keep_ceph_volumes=True"
    break
done
