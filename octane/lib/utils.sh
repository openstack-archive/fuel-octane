#!/bin/bash

PSSH_RUN="pssh -i"

set_pssh_hosts() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
    for node in $(list_nodes $1 controller);
    do
        PSSH_RUN+=" -H $node"
    done
}
