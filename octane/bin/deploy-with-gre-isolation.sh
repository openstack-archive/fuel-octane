#!/bin/bash

display_help() {
    echo "Usage: $0 COMMAND ORIG_ENV_ID [SEED_ENV_ID]
COMMAND:
    clone           - create seed env by cloning settings from env identified
                      by ORIG_ENV_ID. No SEED_ENV_ID needed for this command
    prepare         - prepare configuration of seed env for deployment with
                      network isolation
    provision       - configure nodes in the seed env and start provisioning
    deploy          - activate network isolation and start deployment to the
                      environment
    upgrade         - replace original CICs with seed CICs for public and
                      management networks
    help            - display this message and exit"
}

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
upgrade             - isolate orig env CICs and replace them with seed CICs"
}

KEY=0
[ -z "$1" ] && die $(usage)

[ -z "$2" ] && die $(usage)
ORIG_ENV=$2
[ -z "$3" ] && [ "$1" != "clone" ] && die $(usage)
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
        vips_down $SEED_ENV
        for br_name in br-ex br-mgmt
            do
                check_vip_down $SEED_ENV $br_name
                delete_patch_ports $ORIG_ENV $br_name
                create_tunnels $ORIG_ENV $br_name
                remove_tunnels $SEED_ENV $br_name
                create_patch_ports $SEED_ENV $br_name
            done
        ;;
     help)
        display_help
        ;;
     *)
        echo "Invalid command: $1"
        display_help
        exit 1
        ;;
esac

exit 0
# vi:sw=4:ts=4:
