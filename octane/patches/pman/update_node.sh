#!/bin/sh -x

if [ $# -ne 1 ]
then
    echo "Usage: $0 HOSTNAME"
    exit 1
fi


node=$1
target="/usr/share/mcollective/plugins/mcollective/agent/erase_node.rb"
cat erase_node.rb.patch | ssh $node "patch -Np2 $target && service mcollective restart" || :
