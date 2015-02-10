#!/bin/bash

get_orig_ips() {
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
    local br_name
    br_name=${1:-br-mgmt}
    echo $(grep -A2 $br_name: ./deployment_${ENV}/*controller* \
        | sed -nre 's%.*- (([0-9]{1,3}\.){3}[0-9]{1,3})/[0-9]{1,2}.*%\1%p')
}

get_new_vip() {
    local br_name
    br_name=$(echo ${1:-br-mgmt} \
        | awk '/br-ex/ {print "public_vip:"} \
        /br-mgmt/ {print "management_vip:"}')
    [ -n $br_name ] && echo $(grep $br_name ./deployment_${ENV}/*controller* \
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

create_controllers_file() {
# This is the list of controller nodes for environment ENV. It is used to run
# parallel SSH commands on controllers.
    fuel node --env $ENV | grep controller | awk '{print "node-" $1}' \
        > controllers
}

prepare_static_files() {
# Prepare static configuration files for controllers, and the list of
# controllers in the environment.
    create_controllers_file
}

create_bridge() {
    local br_name
    br_name=$1
    $PSSH_RUN "ovs-vsctl add-br $br_name"
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
    local src_node
    local dst_node
    local br_name
    local remote_ip
    local gre_port
    [ -z $1 ] && {
        echo "Empty tunnel source node hostname"
        exit 1
    }
    src_node=$1
    dst_node=$2
    br_name=$3
    remote_ip=$(host $dst_node | grep -Eo '([0-9\.]+)$')
    [ -z $remote_ip ] && {
        echo "Tunnel remote $dst_node not found"
        exit 1
    }
    gre_port=$br_name--gre-$dst_node
    ssh root@$src_node ovs-vsctl add-port $br_name $gre_port -- \
        set Interface $gre_port type=gre options:remote_ip=$remote_ip
}

create_tunnels() {
    local br_name
    local primary
    [ -z $1 ] && {
        echo "Bridge name required"
        exit 1
    }
    br_name=$1
    primary=$(head -1 ./controllers)
    nodes=$(grep -v $primary ./controllers)
    for node in $nodes
        do
            tunnel_from_to $primary $node $br_name
            tunnel_from_to $node $primary $br_name
        done
}

start_controller_deployment() {
# Start deployment of primary controller in the upgraded environment. This will
# cause other controllers to begin deployment as well.
    local node_id
    fuel --env ${ENV} deployment upload
    node_id=`ls deployment_${ENV} \
        | grep primary-controller \
	    | grep -Eo "[0-9]+?"`

    fuel node --env ${ENV} --deploy --node $node_id
    echo "node-$node_id"
}

check_deployment_status() {
    local status
    status=`fuel env --env ${ENV} \
        | grep -Eo "^${ENV} \| [^\|]" \
        | cut -d' ' -f3`
    [ $status -eq 'operational' ] || {
        echo "Environment status is: $status"
        exit 1
    }
}

delete_tunnel() {
}

remove_tunnels() {
    local br_name
    local primary
    local nodes
    [ -z $1 ] && {
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
    local br_name
    local ph_name
    local nodes
    [ -z $1 ] && {
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
                -- set interface type=patch
            ssh root@node-${node_id} ovs-vsctl add-port br-${ph_name} br-${ph_name}--${br_name} \
                -- set interface type=patch
        done
}

set -x

ORIG_ENV="$2"
if [ -z $ORIG_ENV ]
then
    echo "No original env ID specified!" && exit 1
fi
ENV="$3"
if [ -z $ENV ]
then
    echo "No upgraded env ID specified!" && exit 1
fi

PSSH_RUN="pssh --inline-stdout -h controllers"
PSCP_RUN="pscp.pssh -h controllers"


case $1 in
    prepare)
        prepare_deployment_info
	    prepare_static_files
        create_ovs_bridges
        ;;
    start)
        for br_name in br-ex br-mgmt
            do
                create_tunnels $br_name
            done
        start_controller_deployment
        ;;
    stop)
        check_deployment_status
        for br_name in br-ex br-mgmt
            do
                remove_tunnels $br_name
                create_patch $br_name
            done
        ;;
esac

exit 0
# vi:sw=4:ts=4:
