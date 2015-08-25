#!/bin/bash

pycmd() {
    if ! python -c 'import octane'; then
        yum install -y python-paramiko
        pip install --no-index -e "$CWD/.."
    fi
    local opts=""
    if shopt -qo xtrace; then
        opts="--debug -v"
    fi
    octane $opts "$@"
    exit $?
}

get_service_tenant_id() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    local env=$(get_env_by_node $1)
    local filename="${FUEL_CACHE}/env-${env}-service-tenant-id"
    if [ -f "$filename" ]; then
        SERVICE_TENANT_ID=$(cat $filename)
    else
        SERVICE_TENANT_ID=$(ssh root@$(get_host_ip_by_node_id $1) ". openrc;
keystone tenant-get services \
| awk -F\| '\$2 ~ /id/{print \$3}' | tr -d \ ")
    fi
    [ -z "$SERVICE_TENANT_ID" ] &&
    die "Cannot determine service tenant ID for node $1, exiting"
    echo $SERVICE_TENANT_ID > $filename
}


get_deployment_info() {
    local cmd
# Download deployment config from Fuel master for environment ENV to subdir in
# current directory.
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] || mkdir -p "$FUEL_CACHE"
    [ -d "${FUEL_CACHE}/deployment_$1" ] && rm -r ${FUEL_CACHE}/deployment_$1
    cmd=${2:-default}
    fuel deployment --env $1 --$cmd --dir ${FUEL_CACHE}
}

get_deployment_tasks() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] || mkdir -p "$FUEL_CACHE"
    fuel env --env $1 --deployment-task --download --dir ${FUEL_CACHE}
}

upload_deployment_info() {
# Upload deployment configration with modifications to Fuel master for
# environment ENV.
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] &&
    fuel deployment --env $1 --upload --dir $FUEL_CACHE
}

backup_deployment_tasks() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] &&
    [ -d "${FUEL_CACHE}/cluster_$1" ] &&
    cp -pR "${FUEL_CACHE}/cluster_$1" "${FUEL_CACHE}/cluster_$1.orig"
}

upload_deployment_tasks() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] &&
    fuel env --env $1 --deployment-task --upload --dir $FUEL_CACHE
}

backup_deployment_info() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    [ -d "${FUEL_CACHE}/deployment_$1" ] && {
        [ -d "${FUEL_CACHE}/deployment_$1.orig" ] || mkdir "${FUEL_CACHE}/deployment_$1.orig"
        cp -R ${FUEL_CACHE}/deployment_$1/*.yaml ${FUEL_CACHE}/deployment_$1.orig/
    }
}

remove_patch_transformations() {
# Remove add-patch actions for br-ex, br-mgmt bridges. Required to isolate new
# controllers from original environment while physically connected to the same
# L2 segment.
    [ -z "$1" ] && die "No env ID provided, exiting"
    python ${HELPER_PATH}/transformations.py ${FUEL_CACHE}/deployment_$1 remove_patch_ports
}

remove_physical_transformations(){
    [ -z "$1" ] && die "No env ID provided, exiting"
    python ${HELPER_PATH}/transformations.py ${FUEL_CACHE}/deployment_$1 \
        remove_physical_ports
}

disable_ping_checker() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    [ -d "${FUEL_CACHE}/deployment_$1" ] || die "Deployment info directory not found, exiting"
    ls ${FUEL_CACHE}/deployment_$1/** | xargs -I@ sh -c "echo 'run_ping_checker: false' >> @"
}

skip_deployment_tasks() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    [ -d "${FUEL_CACHE}/cluster_$1" ] || die "Cluster info directory not found, exiting"
    python ${HELPER_PATH}/tasks.py ${FUEL_CACHE}/cluster_$1 skip_tasks
}

prepare_seed_deployment_info() {
    [ -z "$1" ] && "No seed env ID provided, exiting"
    disable_ping_checker $1
    remove_predefined_networks $1
    reset_gateways_admin $1
    skip_deployment_tasks $1
}

merge_deployment_info() {
# Merges default and current deployment info for the given environment.
    [ -z "$1" ] && die "no env ID provided, exiting"
    local infodir="${FUEL_CACHE}/deployment_$1"
    [ -d "$infodir" ] || die "directory $infodir not found, exiting"
    mv "${infodir}" "${infodir}.default"
    get_deployment_info $1 download
    [ -d "${infodir}" ] || mkdir ${infodir}
    mv ${infodir}.default/* ${infodir}/ &&
        rmdir ${infodir}.default
}

remove_predefined_networks() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    python $HELPER_PATH/transformations.py ${FUEL_CACHE}/deployment_$1 remove_predefined_nets
}

reset_gateways_admin() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    python ${HELPER_PATH}/transformations.py \
        ${FUEL_CACHE}/deployment_$1 reset_gw_admin
}

create_ovs_bridges() {
    local nodes
    local node
    local br_name
    [ -z "$1" ] && die "No env ID provided, exiting"
    nodes=$(list_nodes $1 '(controller)')
    for node in $nodes
        do
            ssh root@$node apt-get -y install openvswitch-switch
            [ $? -ne 0 ] && die "Cannot install openvswitch, exiting"
            for br_name in br-ex br-mgmt
                do
                    ssh root@$node ovs-vsctl add-br $br_name
                    ssh root@$node ip link set dev $br_name mtu 1450
                done
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
    [ -z "$1" ] && die "No tunnel paramters provided, exiting"
    src_node=$1
    [ -z "$2" ] && die "No tunnel remote parameters provided, exiting"
    dst_node=$2
    [ -z "$3" ] && die "No bridge name provided, exiting"
    br_name=$3
    key=${4:-0}
    remote_ip=$(host $dst_node | grep -Eo '([0-9\.]+)$')
    [ -z "$remote_ip" ] && die "Tunnel remote host $dst_node not found, exiting"
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
    local nodes
    local node
    [ -z "$1" ] && die "No env ID provided, exiting"
    br_name=$2
    roles_re=${3:-'controller'}
    nodes=$(list_nodes $1 "$roles_re")
    primary=$(echo $nodes | cut -d ' ' -f1)
    for node in $nodes
        do
            [ "$node" == "$primary" ] || {
                tunnel_from_to $primary $node $br_name $KEY
                tunnel_from_to $node $primary $br_name $KEY
                KEY=$(expr $KEY + 1)
            }
        done
}

env_action() {
# Start deployment or provisioning of all nodes in the environment, depending on
# second argument. First argument is an ID of env.
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    local env=$1 && shift
    local action=$1 && shift
    local node_ids="$@"
    fuel node --env $env --$action --node $node_ids
    [ $? -ne 0 ] && die "Cannot start $action for env $env, exiting" 2
}

check_neutron_agents() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local l3_nodes=$(fuel2 node list -c roles -c ip | awk -F\| '$2~/controller/{print($3)}' \
        | tr -d ' ' | xargs -I{} ssh root@{} "ps -ef | grep -v \$\$ \
            | grep -q neutron-l3-agent && echo \$(hostname)" 2>/dev/null)
    local dhcp_nodes=$(fuel2 node list -c roles -c ip | awk -F\| '$2~/controller/{print($3)}' \
        | tr -d ' ' | xargs -I{} ssh root@{} "ps -ef | grep -v \$\$ \
            | grep -q neutron-l3-agent && echo \$(hostname)" 2>/dev/null)
    for n in $l3_nodes;
    do
        [ "${n#node-}" == "$1" ] && exit 1
    done
    for n in $dhcp_nodes;
    do
        [ "${n#node-}" == "$1" ] && exit 1
    done
}

check_deployment_status() {
# Verify operational status of environment.
    [ -z "$1" ] && die "No env ID provided, exiting"
    local status=$(fuel env --env $1 \
        | awk -F"|" '/^'$1'/{print $2}' \
        | tr -d ' ')
    [ "$status" == 'new' ] || die "Environment is not operational, exiting"
}

discover_nodes_to_cics() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local node_ids=$(fuel node | awk -F\| '$2~/discover/{print($1)}' \
        | tr -d ' ' | sed ':a;N;$!ba;s/\n/,/g')
    fuel node set --env $1 --node $node_ids --role controller
}

delete_tunnel() {
# Delete tunnel between src_node and dst_node.
    local src_node
    local dst_node
    local br_name
    local gre_port
    [ -z "$1" ] && die "No tunnel parameters provided, exiting"
    src_node=$1
    [ -z "$2" ] && die "Bridge name not specified"
    br_name=$2
    for gre_port in $(list_ports $src_node $br_name | grep $br_name--gre)
        do
            echo $gre_port \
                | xargs -I{} ssh root@$src_node ovs-vsctl del-port $br_name {}
            [ $? -ne 0 ] && die "Cannot delete GRE port, exiting"
        done
}

remove_tunnels() {
# Delete tunnels from 6.0 CICs to replace 5.1 controllers.
    local br_name
    local nodes
    local node
    [ -z "$1" ] && die "No env ID provided, exiting"
    br_name=$2
    nodes=$(list_nodes $1 'controller')
    for node in $nodes
        do
            delete_tunnel $node $br_name
        done
}

list_ports() {
# On the host identified by first argument, list ports in bridge, identified by
# second argument.
    [ -z "$1" ] && die "No hostname and bridge name provided, exiting"
    [ -z "$2" ] && die "No bridge name provided, exiting"
    echo -n "$(ssh root@$1 ovs-vsctl list-ports $2)"
}

create_patch_ports() {
# Create patch interface to connect logical interface to Public or Management
# network to the physical interface to that network.
    local node
    [ -d ${FUEL_CACHE}/deployment_$1.orig ] || die "Deployment information not found for env $1, exiting"
    [ -z "$1" ] && die "No env ID provided, exiting"
    local br_name=$2
    local nodes=$(list_nodes $1 'controller')
    for node in $nodes
        do
            local filename=$(ls ${FUEL_CACHE}/deployment_$1.orig/*_${node#node-}.yaml \
                | head -1)
            ${BINPATH}/create-controller-ports $filename $br_name \
                | xargs -I {} ssh root@$node {}
        done
}

delete_patch_ports() {
    local br_name
    local ph_name
    local node_ids
    local node_id
    local node
    [ -z "$1" ] && die "No env ID and bridge name provided, exiting"
    [ -z "$2" ] && die "No bridge name provided, exiting"
    br_name=$2
    for node in $(list_nodes $1 controller)
        do
            ph_name=$(list_ports $node $br_name \
                | tr -d '"' \
                | sed -nre 's/'$br_name'--(.*)/\1/p')

            ssh root@${node} ovs-vsctl del-port $br_name ${br_name}--${ph_name}
            ssh root@${node} ovs-vsctl del-port $ph_name ${ph_name}--${br_name}
        done
}

apply_disk_settings() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -f "${FUEL_CACHE}/disks.fixture.yaml" ] || die "No disks fixture provided, exiting"
    local disk_file="${FUEL_CACHE}/node_$1/disks.yaml"
    fuel node --node $1 --disk --download --dir $FUEL_CACHE
    ${BINPATH}/copy-node-settings disks $disk_file ${FUEL_CACHE}/disks.fixture.yaml by_name \
        > /tmp/disks_$1.yaml
    mv /tmp/disks_$1.yaml $disk_file
    fuel node --node $1 --disk --upload --dir $FUEL_CACHE
}

apply_network_settings() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -f "${FUEL_CACHE}/interfaces.fixture.yaml" ] || die "No interfaces fixture provided, exiting"
    local iface_file="${FUEL_CACHE}/node_$1/interfaces.yaml"
    fuel node --node $1 --network --download --dir $FUEL_CACHE
    ${BINPATH}/copy-node-settings interfaces $iface_file \
        ${FUEL_CACHE}/interfaces.fixture.yaml > /tmp/interfaces_$1.yaml
    mv /tmp/interfaces_$1.yaml $iface_file
    fuel node --node $1 --network --upload --dir $FUEL_CACHE
}

keep_ceph_partition() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    local disk_file="${FUEL_CACHE}/node_$1/disks.yaml"
    fuel node --node $1 --disk --download --dir ${FUEL_CACHE}
    ${BINPATH}/keep-ceph-partition $disk_file \
        > /tmp/disks-ceph-partition.yaml
    mv /tmp/disks-ceph-partition.yaml $disk_file
    fuel node --node $1 --disk --upload --dir ${FUEL_CACHE}
}

get_node_settings() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -d "$FUEL_CACHE" ] || mkdir -p "$FUEL_CACHE"
    fuel node --node $1 --network --download --dir $FUEL_CACHE
    fuel node --node $1 --disk --download --dir $FUEL_CACHE
}

prepare_fixtures_from_node() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    get_node_settings $1
    mv ${FUEL_CACHE}/node_$1/disks.yaml ${FUEL_CACHE}/disks.fixture.yaml
    mv ${FUEL_CACHE}/node_$1/interfaces.yaml ${FUEL_CACHE}/interfaces.fixture.yaml
    rmdir ${FUEL_CACHE}/node_$1
}

upload_node_settings() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -d "${FUEL_CACHE}/node_$1" ] || die "Local node settings not found, exiting"
    fuel node --node $1 --network --upload --dir $FUEL_CACHE
    fuel node --node $1 --disk --upload --dir $FUEL_CACHE
}

assign_node_to_env() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -z "$2" ] && die "No seed env ID provided, exiting"
    local roles=$(fuel node --node $1 \
        | awk -F\| '/^'$1'/ {gsub(" ", "", $7);print $7}')
    local orig_id=$(get_env_by_node $1)
    if [ "$orig_id" != "None" ]; then
        fuel2 env move node $1 $2 ||
            die "Cannot move node $1 to env $2, exiting"
        wait_for_node $1 discover
    else
        die "Cannot upgrade unallocated node $1"
        #fuel node --node $1 --env $2 set --role ${roles:-controller}
    fi
}

prepare_compute_upgrade() {
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    cic=$(list_nodes $1 controller | head -1)
    scp ${BINPATH}/host_evacuation.sh root@$cic:/var/tmp/
    ssh root@$cic "/var/tmp/host_evacuation.sh node-$2"
}

cleanup_compute_upgrade() {
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    cic=$(list_nodes $1 controller | head -1)
    ssh root@$cic "source openrc; nova service-enable node-$2 nova-compute"
}

prepare_controller_upgrade() {
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    #Required for updating tenant ID in Neutron config on 6.1
    get_service_tenant_id $2
}

upgrade_node_preprovision() {
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    local roles=$(fuel node --node $2 \
        | awk -F\| '$1~/^'$2'/ {gsub(" ", "", $7);print $7}' \
        | sed -re 's%,% %')
# Pre-upgrade checks
    for role in $roles; do
        case $role in
            ceph-osd)
                check_ceph_cluster $2
                ;;
        esac
    done
# Prepare to provisioning
    for role in $roles
        do
            case $role in 
                compute)
                    prepare_compute_upgrade "$@"
                    ;;
                ceph-osd)
                    prepare_osd_node_upgrade $2
                    set_osd_noout $1
                    ;;
                controller)
                    prepare_controller_upgrade "$@"
                    ;;
                *)
                    echo "Role $role unsupported, skipping"
                    ;;
             esac
         done
    assign_node_to_env $2 $1
}

upgrade_node_postprovision() {
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    wait_for_node $2 "provisioned"
}

upgrade_node_predeploy() {
    local isolated="" roles
    if [ "$1" = "--isolated" ]; then
        isolated=$1
        shift
    fi
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    roles=$(fuel node --node $2 \
        | awk -F\| '$1~/^'$2'/ {gsub(" ", "", $8);print $8}' \
        | sed -re 's%,% %')
    if [[ "$roles" =~ controller ]]; then
        get_deployment_info $1
        if [ "$isolated" ]; then
            backup_deployment_info $1
            remove_physical_transformations $1
        fi
        get_deployment_tasks $1
        prepare_seed_deployment_info $1
        merge_deployment_info $1
        upload_deployment_info $1
        upload_deployment_tasks $1
    fi
}

upgrade_node_postdeploy() {
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    local roles=$(fuel node --node $2 \
        | awk -F\| '$1~/^'$2'/ {gsub(" ", "", $7);print $7}' \
        | sed -re 's%,% %')
    wait_for_node $2 "ready"
    for role in $roles
        do
            case $role in
                compute)
                    cleanup_compute_upgrade "$@"
                    ;;
                ceph-osd)
                    unset_osd_noout $1
                    ;;
                controller)
                    neutron_update_admin_tenant_id $1
                    ;;
            esac
        done
    if [ "$3" == "isolated" ]; then
        restore_default_gateway $2
    fi
}

upgrade_node() {
# This function takes IDs of upgrade seed env and a node, deletes the node
# from original env and adds it to the seed env.
    local isolated="" env n
    if [ "$1" = "--isolated" ]; then
        isolated=$1
        shift
    fi
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    env=$1 && shift
    for n in $@; do
        upgrade_node_preprovision $env $n
    done
    env_action $env provision "$@"
    for n in $@; do
        upgrade_node_postprovision $env $n
        upgrade_node_predeploy $isolated $env $n
    done
    env_action $env deploy "$@"
    for n in $@; do
        upgrade_node_postdeploy $env $n $isolated
    done
}

upgrade_cics() {
    [ -z "$1" ] && die "No 5.1.1 env ID provided, exiting"
    [ -z "$2" ] && die "No 6.0 env ID provided, exiting"
    check_deployment_status $2
    set_pssh_hosts $1 && {
        enable_apis
    } && unset PSSH_RUN
    set_pssh_hosts $2 && {
        start_corosync_services
        start_upstart_services
    } && unset PSSH_RUN
    for br_name in br-ex br-mgmt br-prv;
    do
        delete_patch_ports $1 $br_name
    done
    for br_name in br-ex br-mgmt;
    do
        create_patch_ports $2 $br_name
    done
    list_nodes $1 compute | xargs -I{} ${BINPATH}/upgrade-nova-compute.sh {}
}

upgrade_ceph() {
    [ -z "$1" ] && die "No 5.1 and 6.0 env IDs provided, exiting"
    [ -z "$2" ] && die "No 6.0 env ID provided, exiting"
    ceph_extract_conf $1
    ceph_set_new_mons "$@"
    ceph_push_update_conf $2
    import_bootstrap_osd $2
    prepare_ceph_osd_upgrade $2
}

neutron_update_admin_tenant_id() {
    local tenant_id=''
    [ -z "$1" ] && die "No env ID provided, exiting"
    cic_node=$(list_nodes $1 controller | head -1)
    list_nodes $1 controller | xargs -I{} ssh root@{} \
        "sed -re 's/^(nova_admin_tenant_id )=.*/\1 = $SERVICE_TENANT_ID/' \
-i /etc/neutron/neutron.conf;
restart neutron-server"
}

cleanup_nova_services() {
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    local cic=$(list_nodes $1 controller | head -1)
    ssh root@${cic} '. /root/openrc;
    nova service-list | grep nova \
    | grep -Ev "('$(list_nodes $1 "(controller|compute|ceph-osd)" \
    | sed ':a;N;$!ba;s/\n/|/g')')"' | awk -F \| '{print($2)}' | tr -d ' ' \
    | xargs -I{} ssh root@${cic} ". /root/openrc; nova service-delete {}"
}

cleanup_neutron_services() {
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    local cic=$(list_nodes $1 controller | head -1)
    ssh root@${cic} '. /root/openrc;
    neutron agent-list | grep neutron \
    | grep -Ev "('$(list_nodes $1 "(controller|compute|ceph-osd)" \
    | sed ':a;N;$!ba;s/\n/|/g')')"' | awk -F \| '{print($2)}' | tr -d ' ' \
    | xargs -I{} ssh root@${cic} ". /root/openrc; neutron agent-delete {}"
}

delete_fuel_resources() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local node=$(list_nodes $1 controller | head -1)
    local host=$(get_host_ip_by_node_id ${node#node-})
    scp $HELPER_PATH/delete_fuel_resources.py root@$host:/tmp
    ssh root@$host ". openrc; python /tmp/delete_fuel_resources.py"
}

cleanup_fuel() {
   revert_prepare_fuel
}
