#!/bin/bash

clone_env() {
# Clone settings of the environment specified by ID in the first argument using
# helper Python script `clone-env'
    [ -z "$1" ] && die "Cannot clone environment with empty ID, exiting"
    [ -d "./cluster_$1" ] && rm -r "./cluster_$1"
    echo $(./clone-env --upgrade "$1")
}

get_vip_from_cics() {
# Return VIP of the given type (management or external) assgined to the original
# environment.
    local br_name
    [ -z "$1" ] && die "No environment ID and bridge name provided, exiting"
    [ -z "$2" ] && die "No bridge name provided, exiting"
    br_name=$(echo $2 \
        | awk '/br-ex/ {print "hapr-p"} \
        /br-mgmt/ {print "hapr-m"}')
    [ -n "$1" ] && echo $(fuel nodes --env-id $1 \
            | grep controller \
            | cut -d\| -f5  \
            | xargs -I{} ssh root@{} ip netns exec haproxy ip addr\
            | awk '/'$br_name':/ {getline; getline; print $2}' \
            | sed -re 's%([^/]+)/[0-9]{2}%\1%')
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
    fuel env --env $1 --deployment-task --download --dir ${FUEL_CACHE}
}

upload_deployment_info() {
# Upload deployment configration with modifications to Fuel master for
# environment ENV.
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] &&
    fuel deployment --env $1 --upload --dir $FUEL_CACHE &&
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

prepare_seed_deployment_info_nailgun() {
    [ -z "$1" ] && "No orig and seed env ID provided, exiting"
    [ -z "$2" ] && "No seed env ID provided, exiting"
    get_deployment_info $2
    update_seed_ips "$@"
    get_deployment_info $2
    backup_deployment_info $2
    disable_ping_checker $2
    remove_physical_transformations $2
    remove_predefined_networks $2
    reset_gateways_admin $2
    skip_deployment_tasks $2
    upload_deployment_info $2
}

update_seed_ips() {
    [ -z "$1" ] && "No orig and seed env ID provided, exiting"
    [ -z "$2" ] && "No seed env ID provided, exiting"
    for br_name in br-ex br-mgmt
        do
            update_ips_nailgun_db $1 $2 $br_name
            update_vip_nailgun_db $1 $2 $br_name
        done
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

prepare_cic_disk_fixture() {
    local node_id
    [ -z "$1" ] && die "No env ID provided, exiting"
    node_id=$(fuel node --env $1 | awk '/'${2:-controller}'/{print($1)}' | head -1)
    fuel node --node $node_id --disk --download --dir $FUEL_CACHE
    [ -f "${FUEL_CACHE}/node_$node_id/disks.yaml" ] &&
    cp ${FUEL_CACHE}/node_$node_id/disks.yaml ${FUEL_CACHE}/disks.fixture.yaml
}

prepare_cic_network_fixture() {
    local node_id
    [ -z "$1" ] && die "No env ID provided, exiting"
    node_id=$(fuel node --env $1 | awk '/'${2:-controller}'/{print($1)}' | head -1)
    fuel node --node $node_id --network --download --dir $FUEL_CACHE
    [ -f "${FUEL_CACHE}/node_$node_id/interfaces.yaml" ] &&
    cp ${FUEL_CACHE}/node_$node_id/interfaces.yaml ${FUEL_CACHE}/interfaces.fixture.yaml
}

list_nodes() {
    local roles_re
    [ -z "$1" ] && die "No env ID provided, exiting"
    roles_re=${2:-controller}
    echo "$(fuel node --env $1 \
        | awk -F\| '($7 ~ /'$roles_re'/ || $8 ~ /'$roles_re'/) && $2 ~ /'$3'/ {
                gsub(" ","",$1); print "node-" $1
            }')"
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
    local node_ids
    local mode
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    node_ids=$(fuel node --env $1 \
        | awk 'BEGIN {f = ""}
        /(controller|compute|ceph)/ {
            if (f == "") {f = $1}
            else {printf f","; f = $1}
        }
        END {printf f}')
    fuel node --env $1 --$2 --node $node_ids
    [ $? -ne 0 ] && die "Cannot start $2 for env $1, exiting" 2
}

check_deployment_status() {
# Verify operational status of environment.
    local status
    [ -z "$1" ] && die "No env ID provided, exiting"
    status=$(fuel env --env $1 \
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
            local filename=$(ls ${FUEL_CACHE}/deployment_$1.orig/*_${node_#node-}.yaml \
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
    local disk_file
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -f "disks.fixture.yaml" ] || die "No disks fixture provided, exiting"
    disk_file="${FUEL_CACHE}/node_$1/disks.yaml"
    fuel node --node $1 --disk --download --dir $FUEL_CACHE
    ${BINPATH}/copy-node-settings disks $disk_file ${FUEL_CACHE}/disks.fixture.yaml by_name \
        > /tmp/disks_$1.yaml
    mv /tmp/disks_$1.yaml $disk_file
    fuel node --node $1 --disk --upload --dir $FUEL_CACHE
}

apply_network_settings() {
    local iface_file
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -f "interfaces.fixture.yaml" ] || die "No interfaces fixture provided, exiting"
    iface_file="${FUEL_CACHE}/node_$1/interfaces.yaml"
    fuel node --node $1 --network --download --dir $FUEL_CACHE
    ${BINPATH}/copy-node-settings interfaces $iface_file \
        ${FUEL_CACHE}/interfaces.fixture.yaml > /tmp/interfaces_$1.yaml
    mv /tmp/interfaces_$1.yaml $iface_file
    fuel node --node $1 --network --upload --dir $FUEL_CACHE
}

get_node_settings() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -d "$FUEL_NODE" ] || mkdir -p "$FUEL_CACHE"
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

get_bootable_mac() {
    local port1
    local port2
    local port3
    [ -z "$1" ] && die "No node ID provided, exiting"
    port1=$(ssh "root@node-$1" "ovs-vsctl list-ifaces br-fw-admin")
    port2=$(ssh "root@node-$1" "ovs-vsctl list interface $port1" |
            awk -F\" '/^options/ { print $2; }')
    port3=$(ssh "root@node-$1" "ovs-vsctl list-ifaces \$(ovs-vsctl port-to-br $port2)" | grep -v $port2)
    ssh "root@node-$1" "ip link show $port3" | awk '/link\/ether/{print $2}'
}

delete_node_preserve_id() {
    [ -z "$1" ] && die "${FUNCNAME}: No node ID provided, exiting"
    local node_values=$(echo "SELECT uuid, name
                              FROM nodes WHERE id = $1;" | \
                  $PG_CMD | \
                  sed -e "s/^/'/g" -e "s/$/'/g" -e "s/|/', '/g"
                  )
    local node_mac=$(get_bootable_mac "$1")
    local node_ip=$(get_host_ip_by_node_id "$1")
    fuel node --node $1 --env $orig_id --delete-from-db --force
    while :;
    do
        [ -z "$(fuel node --node $1 | grep ^$1)" ] &&
        echo "${FUNCNAME}: Node $1 was deleted from DB; deleting from Cobbler" &&
        break
        sleep 3
    done
    dockerctl shell cobbler cobbler system remove --name node-$1
    echo "INSERT INTO nodes (id, uuid, name, mac, status, meta,
                             timestamp, online, pending_addition,
                             pending_deletion)
          VALUES ($1, $node_values, '$node_mac', 'discover',
                  '{\"disks\": [], \"interfaces\": []}', now(), false,
                  false, false);" | $PG_CMD
    ssh root@$node_ip shutdown -r now
    while :
        do
            node_online=$(get_node_online $1)
            [ "$node_online" == "True" ] && {
                echo "Node $1 came back online."
                break
            }
            sleep 30
        done
}

assign_node_to_env(){
    local node_mac
    local id
    local node_values
    local node_online
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -z "$2" ] && die "No seed env ID provided, exiting"
    local roles=$(fuel node --node $1 \
        | awk -F\| '/^'$1'/ {gsub(" ", "", $7);print $7}')
    # TODO(ogelbukh) Check that $orig_id is either 'None' or the ID of upgrade
    # target environment. Don't let upgrade arbitrary node from other
    # environment by mistake.
    local orig_id=$(get_env_by_node $1)
    local host=$(get_host_ip_by_node_id $1)
    if [ "$orig_id" != "None" ]
        then
            prepare_fixtures_from_node "$1"
            delete_node_preserve_id "$1"
        else
            local orig_node=$(list_nodes $orig_id $roles)
            [ -z "$orig_node" ] && die "${FUNCNAME}: No node with roles $roles in env $orig_id, exiting"
            prepare_fixtures_from_node $orig_node
        fi
    fuel node --node $1 --env $2 set --role ${roles:-compute,ceph-osd}
    apply_network_settings $1
    apply_disk_settings $1
    echo "$roles" | grep -q ceph-osd &&
        ${BINDIR}/keep-ceph-partition ${FUEL_CACHE}/node_$1/disks.yaml \
            > /tmp/disks-ceph-partition.yaml
    mv /tmp/disks-ceph-partition.yaml ${FUEL_CACHE}/node_$1/disks.yaml
    upload_node_settings $1
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

upgrade_node() {
    local role
    local id
    [ -z "$1" ] && die "No 6.0 env and node ID provided, exiting"
    [ -z "$2" ] && die "No node ID provided, exiting"
    local roles=$(fuel node --node $2 \
        | awk -F\| '/^'$2'/ {gsub(" ", "", $7);print $7}' \
        | sed -re 's%,% %')
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
                *)
                    echo "Role $role unsupported, skipping"
                    ;;
             esac
         done
    assign_node_to_env $2 $1
    fuel node --env $1 --node $2 --provision
    wait_for_node $2 "provisioned"
    get_deployment_info $1 download
    rmdir ${FUEL_CACHE}/deployment_$1.download
    mv ${FUEL_CACHE}/deployment_$1 ${FUEL_CACHE}/deployment_$1.download
    get_deployment_info $1
    mv ${FUEL_CACHE}/deployment_$1.download/* ${FUEL_CACHE}/deployment_$1/
    for br_name in br-ex br-mgmt
        do
            get_ips_from_cics $1 $br_name > "/tmp/env-$1-cic-$br_name-ips"
            filename=$(echo $roles | cut -d ' ' -f 1)_$2.yaml
            discard_ips=$(get_ips_from_deploy_info $1 $br_name $filename)
            replace_ip_addresses $1 $1 $br_name $discard_ips
            replace_vip_address $1 $1 $br_name $filename
        done
    remove_predefined_networks $1
    upload_deployment_info $1
    fuel node --env $1 --node $2 --deploy
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
            esac
        done
}

upgrade_cics() {
    [ -z "$1" ] && die "$FUNCNAME: No 5.1.1 env ID provided, exiting"
    [ -z "$2" ] && die "$FUNCNAME: No 6.0 env ID provided, exiting"
    check_deployment_status $2
    set_pssh_hosts $1 && {
        enable_apis
    } && unset PSSH_RUN
    set_pssh_hosts $2 && {
        start_corosync_services
        start_upstart_services
    } && unset PSSH_RUN
    prepare_ceph_admin_upgrade $2
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

provision_node() {
    local env_id
    [ -z "$1" ] && die "No node ID provided, exiting"
    env_id=$(get_env_by_node $1)
    [ -f "${FUEL_CACHE}/interfaces.fixture.yaml" ] && apply_network_settings $1
    [ -f "${FUEL_CACHE}/disks.fixture.yaml" ] && apply_disk_settings $1
    fuel node --env $env_id --node $1 --provision
}

upgrade_db() {
    [ -z "$1" ] && die "No 5.1 and 6.0 env IDs provided, exiting"
    [ -z "$2" ] && die "No 6.0 env ID provided, exiting"
    local method=${3:mysqldump}
    delete_fuel_resources $2
    sleep 7
    set_pssh_hosts $1 && {
        disable_apis
    } && unset PSSH_RUN
    set_pssh_hosts $2 && {
        stop_corosync_services
        stop_upstart_services
    } && unset PSSH_RUN
    ${method}_from_env $1
    ${method}_restore_to_env $2
    update_admin_tenant_id $2
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

update_admin_tenant_id() {
    local cic_node
    local tenant_id
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    cic_node=$(list_nodes $1 controller | head -1)
    tenant_id=$(ssh root@$cic_node ". openrc; keystone tenant-get services" \
        | awk -F\| '$2 ~ /id/{print $3}' | tr -d \ )
    list_nodes $1 controller | xargs -I{} ssh root@{} \
        "sed -re 's/^(nova_admin_tenant_id )=.*/\1 = $tenant_id/' -i /etc/neutron/neutron.conf;
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

upgrade_env() {
    # TODO(ogelbukh) Modify this function to use 'fuel2 env clone' to create
    # upgrade seed environment.
    [ -z "$1" ] && die "No 5.1 env ID provided, exiting"
    [ -z "$2" ] && die "No node IDs for 6.0 controllers provided, exiting"
    local orig_env=$1 && shift
    local seed_env=$(clone_env $orig_env)
    local args="$orig_env $seed_env"
    copy_generated_settings $args
}

delete_fuel_resources() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local node=$(list_nodes $1 controller | head -1)
    scp $HELPER_PATH/delete_fuel_resources.py \
        root@$(get_host_ip_by_node_id ${node#node-})
    ssh root@$(get_host_ip_by_node_id ${node#node-}) \
        "python delete_fuel_resources.py \$(cat openrc | grep OS_USER \\
        | tr \"='\" ' ' | awk '{print \$3}') \$(cat openrc | grep OS_PASS \\
        | tr\"='\" ' ' | awk '{print \$3}') \$(cat openrc | grep OS_TENANT \\
        | tr \"='\" ' ' | awk '{print \$3}') \$(. openrc; \\
            keystone endpoint-list | egrep ':5000' | awk '{print \$6}')"
}
