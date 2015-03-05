#!/bin/bash

cd $(dirname $0)
. functions

[ "$1" == "-d" ] && {
    set -x
    shift
}

usage() {
    echo "Usage: $(basename $0) [-d] COMMAND ORIG_ID SEED_ID
COMMAND:
clone               - clone envinroment settings and return seed env ID
provision           - start provisioning of nodes in seed env
prepare             - prepare provisioned seed env CICs for isolated deployment
deploy              - start deployment of nodes in seed env with isolation
upgrade             - isolate orig env CICs and replace them with seed CICs
help                - display this message and exit"
}

KEY=0
[ -z "$1" ] && die "$(usage)"

[ -z "$2" ] && die "$(usage)"
ORIG_ENV=$2
[ -z "$3" ] && [ "$1" != "clone" ] && die "$(usage)"
SEED_ENV=$3

case $1 in
    clone)
        SEED_ENV="$(clone_env $ORIG_ENV)"
        copy_generated_settings $ORIG_ENV $SEED_ENV
        echo "6.0 seed environment ID is $SEED_ENV"
        ;;
    provision)
        for node in $(list_nodes $SEED_ENV)
            do
                node_id=$(echo $node | cut -d '-' -f2)
                [ -f ./interfaces.fixture.yaml ] && apply_network_settings $node_id
                [ -f ./disks.fixture.yaml ] && apply_disk_settings $node_id
            done
        env_action $SEED_ENV provision
        ;;
    prepare)
        prepare_seed_deployment_info $ORIG_ENV $SEED_ENV
        create_ovs_bridges $SEED_ENV
        ;;
    deploy)
        for br_name in br-ex br-mgmt
            do
                create_tunnels $SEED_ENV $br_name '(controller|compute|ceph-osd)'
            done
        env_action $SEED_ENV deploy
        ;;
    upgrade)
        check_deployment_status $SEED_ENV
        for br_name in br-ex br-mgmt
            do
                delete_patch_ports $ORIG_ENV $br_name
                create_tunnels $ORIG_ENV $br_name
                remove_tunnels $SEED_ENV $br_name
                create_patch_ports $SEED_ENV $br_name
            done
        ;;
     help)
        usage
        ;;
     *)
        echo "Invalid command: $1"
        usage
        exit 1
        ;;
esac

exit 0
# vi:sw=4:ts=4:
