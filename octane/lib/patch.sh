#!/bin/bash -xe

run=".state"

docker_copyfile() {
    [ -z "$1" ] && die "No source file provided, exiting"
    [ -z "$2" ] && die "No destination file provided, exiting"
    local src=$1 dst=$2
    local tmp="$run/`basename $2`"
    for i in `seq 1 3`; do
        while true
        do
            dockerctl copy $2 $tmp
            cmp -s $1 $tmp && break
            cp $tmp "$tmp.backup"
            dockerctl copy "$@"
            sleep 1
        done
        sleep 1
    done
}

docker_patchfile() {
    [ -z "$1" ] && die "No original file provided, exiting"
    [ -z "$2" ] && die "No patch file provided, exiting"
    local tmp="$run/`basename $1`.patchfile"
    local patch_args="-p1"
    dockerctl copy $1 $tmp
    if [ "$3" == "revert" ]; then
        patch_args="-R ${patch_args}"
    else
        patch_args="-N ${patch_args}"
    fi
    patch $patch_args $tmp $2 && cp $tmp "$tmp.backup" || return 0
    dockerctl copy $tmp $1
    docker_copyfile $tmp $1
}

patchfile() {
    [ -z "$1" ] && die "No original file provided, exiting"
    [ -z "$2" ] && die "No patch file provided, exiting"
    patch -Np1 --dry-run --silent $1 $2 2>/dev/null && patch -Np1 $1 $2
}
