#!/bin/bash -xe

SSH_ARGS="-o LogLevel=quiet"
MON_STATE_PATH=/var/lib/ceph/mon

extract_ceph_conf() {
	sed -nr 's/.*-c ([^ ]+).*/\1/gp'
}

ceph_get_conf_dir() {
    [ -z "$1" ] && die "no CIC node ID provided in args, exiting"
    local ceph_args=$(ssh $SSH_ARGS root@$(get_host_ip_by_node_id $1) \
        "pgrep 'ceph-mon' | xargs ps -fp | grep -m1 '^root '")
    test -z "$ceph_args" &&
        die "no ceph-mon process on node $1"
    local config_path=$(echo $ceph_args | extract_ceph_conf)
    config_path=${config_path:-/etc/ceph/ceph.conf}
#    test -z "$config_path" &&
#        die "Could not extract config_path from $ceph_args on node $1"
    # we assume, ceph keyrings must be placed in ceph.conf directory
    export CEPH_CONF_DIR=$(dirname $config_path)
}

ceph_extract_conf() {
    [ -z "$1" ] && die "No 5.1.1 env ID provided as an arg, exiting"
    check_env_exists $1 ||
        die "Env $1 not found"
    export CEPH_CONF_SRC_NODE=$(list_nodes $1 "controller" | head -1)
    test -z "$CEPH_CONF_SRC_NODE" &&
        die "No controllers found in Env $1"
    local controller1_hostname=$(ssh $SSH_ARGS \
        root@$(get_host_ip_by_node_id ${CEPH_CONF_SRC_NODE#node-}) hostname \
        | cut -d. -f1)
    local controller1_db_path=${MON_STATE_PATH}/ceph-${controller1_hostname}
    ssh $SSH_ARGS $(get_host_ip_by_node_id ${CEPH_CONF_SRC_NODE#node-}) \
        test -d $controller1_db_path  ||
        die "$controller1_db_path not found at $CEPH_CONF_SRC_NODE"
    ceph_get_conf_dir ${CEPH_CONF_SRC_NODE#node-}
    test -z "$CEPH_CONF_DIR" &&
        die "Cannot find Ceph conf dir on $CEPH_CONF_SRC_NODE, exiting"
    ssh $SSH_ARGS root@$(get_host_ip_by_node_id ${CEPH_CONF_SRC_NODE#node-}) \
        "tar cvf - $CEPH_CONF_DIR $controller1_db_path | gzip" \
        | cat - > ${FUEL_CACHE}/env-$1-ceph.conf.tar.gz
}

ceph_set_new_mons() {
    [ -z "$1" ] && die "No 5.1.1 env ID provided as an arg, exiting"
    [ -z "$2" ] && die "no 6.0 env ID provided as an arg, exiting"
    for env in "$@"; do
        check_env_exists $env ||
            die "Env $env not found"
    done
    local controller1=$(list_nodes $1 "controller" | head -1)
    test -z "$controller1" &&
        die "No controllers found in Env $1"
    local controllers=$(list_nodes $2 "controller")
    test -z "$controllers" &&
        die "No controllers found in Env $1"
    local controllers_hostnames=$(echo -n $controllers | xargs -I{} \
        ssh $SSH_ARGS root@{} hostname | cut -d. -f1)
    local source_controllers=$(ssh $SSH_AGS root@$controller1 \
        cat ${CEPH_CONF_DIR}/ceph.conf \
        | awk -F= '$1 = /mon_host/ {print gensub("^ ", "", "", $2)}')
    local source_controllers_mask=$(echo ${source_controllers} | sed 's/ /|/g')
    # init global vars for Ceph config values
    export MON_INITIAL_MEMBERS=""
    export MON_HOSTS=""
    # collect avialable dst controllers
    for ctrl_host in ${controllers}; do
        ip_match=`ssh $SSH_ARGS $ctrl_host ip addr \
            | grep -m1 -E "${source_controllers_mask}" \
            | sed -r 's/[ ]+?inet ([^\/]+).*/\1/'`
        test -z "$ip_match" && continue
        export MON_INITIAL_MEMBERS="$MON_INITIAL_MEMBERS `ssh $SSH_ARGS $ctrl_host hostname | cut -d. -f1`"
        export MON_HOSTS="$MON_HOSTS $ip_match"
    done
}

ceph_push_update_conf() {
    [ -z "$1" ] && die "no 6.0 env ID provided as an arg, exiting"
    local dst_base_dir=""
    local ctrl_host_db_path
    local controller1_db_path=${MON_STATE_PATH}/ceph-${CEPH_CONF_SRC_NODE}
    local ceph_conf_dir
    local orig_env=$(get_env_by_node ${CEPH_CONF_SRC_NODE#node-})
    for ctrl_host in ${MON_INITIAL_MEMBERS}; do
        ctrl_host_db_path="${MON_STATE_PATH}/ceph-${ctrl_host}"
        ceph_get_conf_dir ${ctrl_host#node-}
        ssh $SSH_ARGS root@$(get_host_ip_by_node_id ${ctrl_host#node-}) \
            "rm -rf $CEPH_CONF_DIR;
             mkdir $CEPH_CONF_DIR;
             test -d $ctrl_host_db_path && rm -rf $ctrl_host_db_path;
             :"
        cat ${FUEL_CACHE}/env-${orig_env}-ceph.conf.tar.gz \
            | ssh $SSH_ARGS $ctrl_host "gunzip | tar xvf - -C /"
        ssh $SSH_ARGS root@$(get_host_ip_by_node_id ${ctrl_host#node-}) "
        set -ex
        mv $controller1_db_path $ctrl_host_db_path
        sed -i'' 's/^mon_initial_members =.*/mon_initial_members =$MON_INITIAL_MEMBERS/g;
              s/^mon_host =.*/mon_host =$MON_HOSTS/g;
              s/^host =.*/host = ${ctrl_host}/g' ${CEPH_CONF_DIR}/ceph.conf 

        cat ${CEPH_CONF_DIR}/ceph.conf | awk -F= '
            \$1 ~ /^fsid/ {
                fsid = \$2
            } 
            \$1 ~ /^mon_initial_members/ {
                split(\$2, members, \" \")
            }
            \$1 ~ /^mon_host/ {
                split(\$2, host, \" \")
            }
            END {
                printf(\"monmaptool --fsid %s --clobber --create \", fsid)
                for (i in members) {
                    printf(\" --add %s %s\", members[i], host[i]);
                } 
                printf(\" /tmp/monmap\n\")
            }' | sh -

        ceph-mon -i ${ctrl_host} --inject-monmap /tmp/monmap 
      " 
    done
    for ctrl_host in "${MON_INITIAL_MEMBERS# }"; do
        ssh root@$ctrl_host "restart ceph-mon id=$ctrl_host"
    done
}

import_bootstrap_osd() {
    local node
    [ -z "$1" ] && die "No env ID provided, exiting"
    node=$(list_nodes $1 controller | head -1)
    ssh root@$(get_host_ip_by_node_id ${node#node-}) \
        ceph auth import -i /root/ceph.bootstrap-osd.keyring
    ssh root@$(get_host_ip_by_node_id ${node#node-}) \
        ceph auth caps client.bootstrap-osd mon 'allow profile bootstrap-osd'
}

prepare_ceph_osd_upgrade() {
    local seed_id
    local nodes
    local node
    [ -z "${seed_id:=$1}" ] && die "No 6.0 env ID provided, exiting"
    nodes=$(list_nodes $seed_id '(controller)')
    for node in $nodes
        do
            ssh root@$node sh -c "'
                f=\$(mktemp)
                awk -f /dev/stdin /etc/ceph/ceph.conf > \$f
                mv \$f /etc/ceph/ceph.conf
            '" <<EOF
BEGIN {
    flag = 0
}
/^$|^\[/ && flag == 1 {
    flag = 0;
    print "osd_crush_update_on_start = false"
}
/^\[global\]$/ {
    flag = 1
}
{ print \$0 }
EOF
        done
}

set_osd_noout() {
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    ssh root@$(list_nodes $1 'controller' | head -1) ceph osd set noout
}

unset_osd_noout() {
    [ -z "$1" ] && die "No 6.0 env ID provided, exiting"
    ssh root@$(list_nodes $1 'controller' | head -1) ceph osd unset noout
}

check_ceph_cluster() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    [ -z "$(ssh root@node-$1 ceph health | grep HEALTH_OK)" ] && \
        die "Ceph cluster is unhealthy, exiting"
}

patch_osd_node() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    cd ${PATCH_DIR}/pman/
    ./update_node.sh node-$1
    cd $OLDPWD
}

prepare_osd_node_upgrade() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    check_ceph_cluster "$@"
    patch_osd_node "$@"
}

restart_mon_init() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    ssh root@$(get_host_ip_by_node_id $1) "stop ceph-mon id=node-$1;
        /etc/init.d/ceph start mon" ||
    die "Cannot restart Ceph MON on node $1, exiting"
}
