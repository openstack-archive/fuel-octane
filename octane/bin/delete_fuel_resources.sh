#!/bin/bash

[ "$1" == "-d" ] && {
    set -x
    shift
}

[ -z "$1" ] && die "$(usage)"
ENV=$1

controller="$(fuel node --env $ENV | awk '/controller/ {print "node-" $1}' | head -n 1)"

scp ../helpers/delete_fuel_resources.py $controller:
ssh $controller "python delete_fuel_resources.py \$(cat openrc | grep OS_USER | tr \"='\" ' ' | awk '{print \$3}') \$(cat openrc | grep OS_PASS | tr \"='\" ' ' | awk '{print \$3}') \$(cat openrc | grep OS_TENANT | tr \"='\" ' ' | awk '{print \$3}') \$(. openrc; keystone endpoint-list | egrep ':5000' | awk '{print \$6}')"
