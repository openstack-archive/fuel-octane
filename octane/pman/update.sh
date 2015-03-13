#!/bin/sh -ex

run=.state

function copyfile() {
    local src=$1 dst=$2
    local tmp="$run/`basename $dst`"
    for i in `seq 1 3`; do
        while true
        do
            dockerctl copy $dst $tmp
            cmp -s $src $tmp && break
            cp $tmp "$tmp.backup"
            dockerctl copy $src $dst
            sleep 1
        done
        sleep 1
    done
}

function patchfile() {
    local orig=$1 patchf=$2
    local tmp="$run/`basename $orig`"
    dockerctl copy $orig $tmp
    patch -Np4 $tmp $patchf && cp $tmp "$tmp.backup" || return 0
    dockerctl copy $tmp $orig
}

mkdir -p $run
dockerctl restart cobbler
copyfile ./pmanager.py cobbler:/usr/lib/python2.6/site-packages/cobbler/pmanager.py
patchfile nailgun:/usr/lib/python2.6/site-packages/nailgun/volumes/manager.py manager.py.patch
dockerctl shell nailgun pkill -f wsgi
