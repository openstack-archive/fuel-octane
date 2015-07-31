# vim: syntax=sh
REVERT_PATH="$(readlink -e "$BASH_SOURCE")"
OCTANE_PATH="$(readlink -e "$(dirname "$REVERT_PATH")/..")"

## functions

revert_prepare_osd_upgrade () {
    local env_id
    local cic_node
    [ -z "$1" ] && die "No node ID provided, exiting"
    env_id=$(get_env_by_node $1)
    cic_node=$(list_nodes $env_id 'controller' | head -1)
    [ -z "$(ssh root@$cic_node ceph health | grep HEALTH_OK)" ] && \
        die "Ceph cluster is unhealthy, exiting"
    ssh root@$ctrl ceph osd unset noout
    revert_pman_udate_node node-$1
}

revert_prepare_fuel () {
    revert_prepare_osd_upgrade
    revert_patch_fuel_components puppet
    revert_all_patches
}

revert_deployment_tasks() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
    [ -d "$FUEL_CACHE" ] &&
    [ -d "${FUEL_CACHE}/cluster_$1" ] &&
    cp -pR "${FUEL_CACHE}/cluster_$1.orig" "${FUEL_CACHE}/cluster_$1"
}

restore_default_gateway() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    local env_id=$(get_env_by_node $1)
    local nodefile=$(ls ${FUEL_CACHE}/deployment_${env_id}/*_$1.yaml | head -1)
    local gw_ip=$(python -c "import yaml;
with open('"${nodefile}"') as f:
  config = yaml.safe_load(f)
  ints = config['network_scheme']['endpoints']
  print ints['br-ex']['gateway']")
    ssh root@node-$1 "ip route delete default;
        ip route add default via $gw_ip"
    done
}

revert_patch_fuel_components() {
    local cmp
    [ -z "$1" ] && die "No component name provided, exiting"
    for cmp in "$@";
    do
        [ -d "$PATCH_DIR/$cmp" ] || die "No dir for component $cmp, exiting"
        pushd "$PATCH_DIR/$cmp"
        [ -x "./revert.sh" ] && ./revert.sh
        popd
    done
}

function revert_all_patches() { 
        PATCH_EXTRA_ARGS="-R" patch_all_containers
} 
