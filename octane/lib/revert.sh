# vim: syntax=sh
REVERT_PATH="$(readlink -e "$BASH_SOURCE")"
OCTANE_PATH="$(readlink -e "$(dirname "$REVERT_PATH")/..")"

## functions

revert_prepare_fuel () {
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
