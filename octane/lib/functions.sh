#!/bin/bash

pycmd() {
    if ! python -c 'import octane'; then
        yum install -y python-paramiko
        pip install --no-index -e "$CWD/.." ||
        die "Cannot install octane, exiting"
    fi
    local opts=""
    if shopt -qo xtrace; then
        opts="--debug -v"
    fi
    octane $opts "$@"
    exit $?
}

check_deployment_status() {
# Verify operational status of environment.
    [ -z "$1" ] && die "No env ID provided, exiting"
    local status=$(fuel env --env $1 \
        | awk -F"|" '/^'$1'/{print $2}' \
        | tr -d ' ')
    [ "$status" == 'new' ] || die "Environment is not operational, exiting"
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
