#!/bin/bash

get_nailgun_db_pass() {
# Parse nailgun configuration to get DB password for 'nailgun' database. Return
# the password.
    echo $(dockerctl shell nailgun cat /etc/nailgun/settings.yaml \
        | awk 'BEGIN {out=""}
               /DATABASE/ {out=$0;next}
               /passwd:/ {if(out!=""){out="";print $2}}' \
        | tr -d '"')
}

PG_CMD="psql -At postgresql://nailgun:$(get_nailgun_db_pass)@localhost/nailgun"

get_node_group_id() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    echo "select id from nodegroups where cluster_id = $1" \
        | $PG_CMD
}

get_nailgun_net_id() {
    local vip_type
    local net_id
    local group_id
    [ -z "$1" ] && die "No group ID provided, exiting"
    [ -z "$2" ] && die "No bridge name provided, exiting"
    group_id=$(get_node_group_id $1) 
    vip_type=$(echo $2 | sed -e 's/br-ex/public/;s/br-mgmt/management/')
    net_id=$(echo "select id from network_groups where group_id = ${group_id} and
        name = '$vip_type';" | $PG_CMD)
    echo $net_id
}

update_vip_nailgun_db() {
# Replace Virtual IP addresses assgined to 6.0 Seed environment in Nailgun DB
# with addresses from 5.1 environment
    local vip
    local seed_net_id
    local orig_net_id
    [ -z "$1" ] && die "No 5.1 and 6.0 env IDs provided, exiting"
    [ -z "$2" ] && die "No 6.0 env ID provided, exiting"
    [ -z "$3" ] && die "No bridge provided, exiting"
    orig_net_id=$(get_nailgun_net_id $1 $3)

    seed_net_id=$(get_nailgun_net_id $2 $3)
    vip=$(echo "select ip_addr from ip_addrs where network = $orig_net_id and
        node is null and vip_type = 'haproxy';" | $PG_CMD)
    echo "update ip_addrs set ip_addr = '$vip' where network = $seed_net_id and
        node is null and vip_type = 'haproxy';" | $PG_CMD
}

update_ips_nailgun_db() {
    local orig_net_id
    local seed_net_id
    local tmpfile
    local node
    [ -z "$1" ] && die "No 5.1 and 6.0 env IDs provided, exiting"
    [ -z "$2" ] && die "No 6.0 env ID provided, exiting"
    [ -z "$3" ] && die "No bridge provided, exiting"
    orig_net_id=$(get_nailgun_net_id $1 $3)
    seed_net_id=$(get_nailgun_net_id $2 $3)
    tmpfile="/tmp/env-$1-cics-$3-ips"
    list_nodes $1 controller | sed -re "s,node-(.*),\1," | sort > $tmpfile
    for node in $(list_nodes $2 controller | sed -re "s,node-(.*),\1," | sort)
        do
            orig_node=$(sed -i -e '1 w /dev/stdout' -e '1d' "$tmpfile")
            echo "DROP TABLE IF EXISTS ip_$$;
		SELECT ip_addr INTO ip_$$ FROM ip_addrs WHERE node = $orig_node AND network = $orig_net_id;
                DELETE FROM ip_addrs WHERE node = $node AND network = $seed_net_id;
                INSERT INTO ip_addrs VALUES(DEFAULT, $seed_net_id, $node,
                (SELECT ip_addr FROM ip_$$), DEFAULT);
            " | $PG_CMD
        done
}

copy_generated_settings() {
# Update configuration of 6.0 environment in Nailgun DB to preserve generated
# parameters values from the original environmen.
    local generated
    [ -z "$1" ] && die "No 5.1 env ID provided, exiting"
    [ -z "$2" ] && die "No 6.0 env ID provided, exiting"
    generated=$(echo "select generated from attributes where cluster_id = $2;
select generated from attributes where cluster_id = $1;" \
        | $PG_CMD \
        | grep -v ^$ \
        | python ../helpers/join-jsons.py);
    [ -z "$generated" ] && die "No generated attributes found for env $1"
    echo "update attributes set generated = '$generated' where cluster_id = $2" \
        | $PG_CMD
}
