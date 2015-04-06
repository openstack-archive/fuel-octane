#!/bin/sh -ex

run=".state"
PATCH_DIR=$(dirname $0)

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
    local src=$1 patchf=$2
    local tmp="$run/`basename $src`.patchfile"
    dockerctl copy $src $tmp
    patch -Np1 $tmp $patchf && cp $tmp "$tmp.backup" || return 0
    dockerctl copy $tmp $src
    copyfile $tmp $src
}

mkdir -p $run
dockerctl restart cobbler
sleep 10
patchfile cobbler:/usr/lib/python2.6/site-packages/cobbler/pmanager.py ${PATCH_DIR}/pmanager.py.patch
sleep 5
patchfile cobbler:/usr/lib/python2.6/site-packages/cobbler/pmanager.py ${PATCH_DIR}/pmanager.py.patch
patchfile nailgun:/usr/lib/python2.6/site-packages/nailgun/volumes/manager.py ${PATCH_DIR}/manager.py.patch
dockerctl shell nailgun pkill -f wsgi
