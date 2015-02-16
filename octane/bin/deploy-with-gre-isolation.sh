#!/bin/bash

clone_env() {
# Clone settings of the environment specified by ID in the first argument using
# helper Python script `clone-env'
    local env_id
    env_name=$(fuel env --env $1 | awk '/operational/ {print $5}')
    [ -n "$env_name" ] || {
        echo "No environment found with ID of $1"
        exit 1
    }
    [ -d "$env_name" ] && {
        echo "Directory $env_name exists"
        exit 1
    }
    env_id=$(./clone-env --upgrade $env_name)
    [ -n "$env_name" ] || {
        echo "Cannot clone environment $env_name"
        exit 1
    }
    echo $env_id
}

get_orig_ips() {
# Return a list of addresses assigned to the bridge identified by its name in
# the first argument on nodes in the original environment.
    local br_name
    br_name=${1:-br-mgmt}
    echo $(fuel nodes --env-id $ORIG_ENV \
        | grep controller \
        | cut -d\| -f5  \
        | xargs -I{} ssh root@{} ip addr\
        | awk '/'$br_name':/ {getline; getline; print $2}' \
        | sed -re 's%([^/]+)/[0-9]{2}%\1%')
}

get_orig_vip() {
# Return VIP of the given type (management or external) assgined to the original
# environment.
    local br_name
    local orig_vip
    br_name=$(echo ${1:-br-mgmt} \
        | awk '/br-ex/ {print "hapr-p"} \
        /br-mgmt/ {print "hapr-m"}')
    [ -n "$br_name" ] && echo $(fuel nodes --env-id $ORIG_ENV \
            | grep controller \
            | cut -d\| -f5  \
            | xargs -I{} ssh root@{} ip netns exec haproxy ip addr\
            | awk '/'$br_name':/ {getline; getline; print $2}' \
            | sed -re 's%([^/]+)/[0-9]{2}%\1%')
}

get_deployment_info() {
# Download deployment config from Fuel master for environment ENV to subdir in
# current directory. Skip download if the directory already exists.
    test -d ./deployment_${ENV} || fuel --env ${ENV} deployment default
}

get_new_ips() {
# Returns a list of addresses that Fuel wants to assign to nodes in the 6.0
# deployment. These addresses must be replaced with addresses from the original
# environment.
    local br_name
    br_name=${1:-br-mgmt}
    echo $(grep -A2 $br_name: ./deployment_${ENV}/*controller* \
        | sed -nre 's%.*- (([0-9]{1,3}\.){3}[0-9]{1,3})/[0-9]{1,2}.*%\1%p')
}

get_new_vip() {
# Returns a VIP of given type that Fuel wants to assign to the 6.0 environment
# and that we want to replace with original VIP.
    local br_name
    br_name=$(echo ${1:-br-mgmt} \
        | awk '/br-ex/ {print "public_vip:"} \
        /br-mgmt/ {print "management_vip:"}')
    [ -n $br_name ] && echo $(grep $br_name ./deployment_${ENV}/primary-controller* \
        | awk '{print $2}')
}

upload_deployment_info() {
# Upload deployment configration with modifications to Fuel master for
# environment ENV.
    test -d ./deployment_${ENV} && fuel --env ${ENV} deployment upload
}

replace_ip_addresses() {
# Replace IP addresses assigned to new env's controllers and VIPs with addresses
# of the original environment in deployment config dump.
    local dirname
    local br_name
    local orig_ips
    local orig_vip
    local new_ip
    br_name=$1
    shift
    dirname=deployment_${ENV}
    orig_ips=$(get_orig_ips $br_name)
    for orig_ip in $orig_ips
        do
            if [ -n "$*" ]
                then
                    new_ip=$1
                    sed -i "s%$new_ip%$orig_ip%" $dirname/*.yaml
                    shift
                fi
        done
    orig_vip=$(get_orig_vip $br_name)
    new_vip=$(get_new_vip $br_name)
    sed -i "s%$new_vip%$orig_vip%" $dirname/*.yaml
}

remove_patch_transformations() {
# Remove add-patch actions for br-ex, br-mgmt bridges. Required to isolate new
# controllers from original environment while physically connected to the same
# L2 segment.
    cp -R deployment_${ENV} deployment_${ENV}.orig
    python ../helpers/transformations.py deployment_${ENV}
}

prepare_deployment_info() {
# Prepare deployment configuration of Fuel environment.
    local br_name
    local discard_ips
    get_deployment_info
    for br_name in br-ex br-mgmt
        do
            discard_ips=$(get_new_ips $br_name)
            replace_ip_addresses $br_name $discard_ips
        done
    remove_patch_transformations
    upload_deployment_info
}

create_hosts_file() {
# This is the list of controller nodes for environment ENV. It is used to run
# parallel SSH commands on controllers.
    local hosts
    hosts=${1:-controllers}
    fuel node --env $ENV | awk '/(controller|compute)/ {print "node-" $1}' \
        > $hosts
}

prepare_static_files() {
# Prepare static configuration files for controllers, and the list of
# controllers in the environment.
    create_hosts_file
}

create_bridge() {
    local br_name
    br_name=$1
    $PSSH_RUN "ovs-vsctl add-br $br_name"
    $PSSH_RUN "ip link set dev $br_name mtu 1450"
}

create_ovs_bridges() {
# Install openvswitch to controller nodes and create bridges to ensure fixed MAC
# addresses are known in advance before deployment starts.
    local br_name
    $PSSH_RUN "apt-get -y install openvswitch-switch"
    for br_name in br-ex br-mgmt
        do
            create_bridge $br_name
        done
}

tunnel_from_to() {
# Configure GRE tunnels between 2 nodes. Nodes are specified by their hostnames
# (e.g. node-2). Every tunnel must have unique key to avoid conflicting
# configurations.
    local src_node
    local dst_node
    local br_name
    local remote_ip
    local gre_port
    local key
    [ -z "$1" ] && {
        echo "Empty tunnel source node hostname"
        exit 1
    }
    src_node=$1
    dst_node=$2
    br_name=$3
    key=${4:-0}
    remote_ip=$(host $dst_node | grep -Eo '([0-9\.]+)$')
    [ -z "$remote_ip" ] && {
        echo "Tunnel remote $dst_node not found"
        exit 1
    }
    gre_port=$br_name--gre-$dst_node
    ssh root@$src_node ovs-vsctl add-port $br_name $gre_port -- \
        set Interface $gre_port type=gre options:remote_ip=$remote_ip \
        options:key=$key
}

create_tunnels() {
# Create tunnels between nodes in the new environment to ensure isolation from
# management and public network of original environment and retain connectivity
# in the 6.0 environment.
    local br_name
    local primary
    [ -z "$1" ] && {
        echo "Bridge name required"
        exit 1
    }
    br_name=$1
    primary_id=$(ls deployment_${ENV}/primary-controller_*.yaml\
        | sed -re 's/.*primary-controller_([0-9]+).yaml/\1/')
    primary="node-$primary_id"
    nodes=$(fuel node --env ${ENV} | grep -v "^$primary_id" \
        | awk '/(controller|compute)/ {print "node-" $1}')
    for node in $nodes
        do
            tunnel_from_to $primary $node $br_name $KEY
            tunnel_from_to $node $primary $br_name $KEY
            KEY=$(expr $KEY + 1)
        done
}

get_nailgun_db_pass() {
# Parse nailgun configuration to get DB password for 'nailgun' database. Return
# the password.
    echo $(dockerctl shell nailgun cat /etc/nailgun/settings.yaml \
        | awk 'BEGIN {out=""}
               /DATABASE/ {out=$0;next}
               /passwd:/ {if(out!=""){out="";print $2}}' \
        | tr -d '"')
}

copy_generated_settings() {
# Update configuration of 6.0 environment in Nailgun DB to preserve generated
# parameters values from the original environmen.
    local command
    local db_pass
    db_pass=$(get_nailgun_db_pass)
    [ -n "${ENV}" ] || {
        echo "Environment ID unknown, exiting"
        exit 1
    }
    generated=$(echo "select generated from attributes where cluster_id = ${ENV};
select generated from attributes where cluster_id = ${ORIG_ENV};" \
        | psql -t postgresql://nailgun:$db_pass@localhost/nailgun \
        | grep -v ^$ \
        | python ../helpers/join-jsons.py);
    [ -n "$generated" ] || {
        echo "No generated attributes found for env $ENV"
        exit 1
    }
    echo "update attributes set generated = '$generated' where cluster_id = ${ENV}" \
        | psql -t postgresql://nailgun:$db_pass@localhost/nailgun
}

deploy_env() {
# Start deployment of primary controller in the upgraded environment. This will
# cause other controllers to begin deployment as well.
    local node_id
    fuel --env ${ENV} deployment upload
    node_id=`ls deployment_${ENV} \
        | grep primary-controller \
	    | grep -Eo "[0-9]+?"`
    node_ids=`fuel node --env ${ENV} \
        | awk 'BEGIN {f = ""}
        /(controller|compute|ceph)/ {
            if (f == "") {f = $1}
            else {printf f","; f = $1}
        }
        END {printf f}'`
    fuel node --env ${ENV} --deploy --node $node_ids
    echo "node-$node_id"
}

check_deployment_status() {
# Verify operational status of environment.
    local status
    status=$(fuel env --env ${ENV} \
        | grep -Eo "^${ENV} \| [^\|]+" \
        | cut -d' ' -f3)
    [ "$status" == 'operational' ] || {
        echo "Environment status is: $status"
        exit 1
    }
}

delete_tunnel() {
# Delete tunnel between src_node and dst_node.
    local src_node
    local dst_node
    local br_name
    local remote_ip
    local gre_port
    [ -z "$1" ] && {
        echo "Empty tunnel source hostname"
        exit 1
    }
    src_node=$1
    [ -z "$2" ] && {
        echo "Empty tunnel destination hostname"
        exit 1
    }
    dst_node=$2
    [ -z "$3" ] && {
        echo "Bridge name not specified"
        exit 1
    }
    br_name=$3
    gre_port=$br_name--gre-$dst_node
    ssh root@$src_node ovs-vsctl del-port $br_name $gre_port
}

remove_tunnels() {
# Delete tunnels from 6.0 CICs to replace 5.1 controllers.
    local br_name
    local primary
    local nodes
    [ -z "$1" ] && {
        echo "Bridge name required"
        exit 1
    }
    br_name=$1
    primary=$(head -1 ./controllers)
    nodes=$(grep -v $primary ./controllers)
    for node in $nodes
        do
            delete_tunnel $primary $node $br_name
            delete_tunnel $node $primary $br_name
        done
}

create_patch() {
# Create patch interface to connect logical interface to Public or Management
# network to the physical interface to that network.
    local br_name
    local ph_name
    local nodes
    local node_id
    [ -z "$1" ] && {
        echo "Bridge name required for patch"
        exit 1
    }
    br_name=$1
    node_ids=$(fuel node --env $ENV | awk '/controller/ {print $1}')
# TODO(ogelbukh): Parse original configurations for all controllers, not only
# primary, to identify pairing bridge/physical interface
    for node_id in $node_ids
        do
            ph_name=$(cat deployment_${ENV}.orig/*_$node_id.yaml \
                | sed -n '/- br-ex/{g;1!p;};h' \
                | sed -re 's,.*- (.*),\1,')

            ssh root@node-${node_id} ovs-vsctl add-port $br_name ${br_name}--${ph_name} \
                -- set interface ${br_name}--${ph_name} type=patch options:peer=br-${ph_name}
            ssh root@node-${node_id} ovs-vsctl add-port ${ph_name} ${ph_name}--${br_name} \
                -- set interface ${ph_name}--${br_name} type=patch options:peer=${br_name}
        done
}

delete_patch() {
    local br_name
    local ph_name
    local node_ids
    local node_id
    [ -z "$1" ] && {
        echo "Patch name required to delete patch"
        exit 1
    }
    br_name=$1
    node_ids=$(fuel node --env $ENV | awk '/controller/ {print $1}')
    for node_id in $node_ids
        do
            ph_name=$(ssh root@node-${node_id} ovs-vsctl show \
                | awk 'BEGIN {br=""}
                       /Bridge br-mgmt/ {br=$0;next}
                       /Port/ {if(br!=""){print $2}}
                       /Bridge/ {if(br!=""){br=""}}' \
                | tr -d '"' \
                | sed -re "s/br-mgmt[-]*//;")

            ssh root@node-${node_id} ovs-vsctl del-port \
                $br_name ${br_name}--${ph_name}
            ssh root@node-${node_id} ovs-vsctl del-port \
                $ph_name ${ph_name}--${br_name}
        done
}

isolate_old_controllers() {
# Apply isolation to old controllers in a similar fashion as to new controllers.
    local br_name
    [ -n "$1" ] || {
        echo "No bridge name supplied, exiting"
        exit 1
    }
    br_name=$1
    create_hosts_file controllers.orig
    orig_pssh_run=$PSSH_RUN
    PSSH_RUN="pssh --inline-stdout -h controllers.orig"
    create_tunnels $br_name
    PSSH_RUN=$orig_pssh_run
}

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

set -x

KEY=0
ORIG_ENV="$2"
[ -z "$ORIG_ENV" ] && {
    echo "No original env ID specified!"
    exit 1
}
ENV="$3"

HOSTS_FILE="controllers"
PSSH_RUN="pssh --inline-stdout -h $HOSTS_FILE"
PSCP_RUN="pscp.pssh -h controllers"


case $1 in
    clone)
        ENV="$(clone_env $ORIG_ENV)"
        copy_generated_settings
        echo "6.0 seed environment ID is $ENV"
        ;;
    provision)
        apply_node_settings
        provision_env
        ;;
    prepare)
        prepare_deployment_info
	    prepare_static_files
        create_ovs_bridges
        ;;
    deploy)
        for br_name in br-ex br-mgmt
            do
                create_tunnels $br_name
            done
        deploy_env
        ;;
    upgrade)
        check_deployment_status
        for br_name in br-ex br-mgmt
            do
                delete_patch $br_name
                isolate_old_controllers $br_name
                remove_tunnels $br_name
                create_patch $br_name
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
