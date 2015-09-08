#!/bin/bash

yell() {
    echo "$*" >&2
}

die() {
    yell "${FUNCNAME[1]}: ${1}"
    exit ${2:-1}
}

check_env_exists() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
	local env_id=$1
    fuel env --env-id $env_id  | grep -qE "$env_id[ ]+?\|"
}

set_pssh_hosts() {
    [ -z "$1" ] && die "No environment ID provided, exiting"
    PSSH_RUN="pssh -i"
    for node in $(list_nodes $1 ${2:controller});
    do
        PSSH_RUN+=" -H $node"
    done
}

get_env_by_node() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    echo "$(fuel node --node $1 \
        | awk -F\| '/^'$1'/ {gsub(" ", "", $4); print $4}')"
}

get_host_ip_by_node_id() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    echo $(fuel node | awk -F"|" '/^'$1' /{print($5)}' | tr -d ' ')
}

get_node_online() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    fuel node --node "$1" | tail -1 | awk -F\| '{gsub(" ", "", $9);print($9)}'
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
