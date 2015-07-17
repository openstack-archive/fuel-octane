#!/bin/bash -xe

run=".state"
[ -d "$run" ] || mkdir -p "$run"

patch_fuel_components() {
    local cmp
    [ -z "$1" ] && die "No component name provided, exiting"
    for cmp in "$@";
    do
        [ -d "$PATCH_DIR/$cmp" ] || die "No dir for component $cmp, exiting"
        pushd "$PATCH_DIR/$cmp"
        [ -x "./update.sh" ] && ./update.sh
        popd
    done
}
