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
