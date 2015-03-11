#!/bin/sh

set -x
set -e
SOURCE_ENV_ID=$1
DST_ENV_ID=$2
SSH_ARGS="-o LogLevel=quiet"


if [ -z "$SOURCE_ENV_ID" -o -z "$DST_ENV_ID" ]; then
	echo "Usage $0 <SOURCE_ENV_ID> <DST_ENV_ID>" 
	exit 2
fi

check_env_exists() {
	local env_id=$1
	 fuel env --env-id $env_id  | grep -qE "$env_id[ ]+?\|"  
} 

get_env_nodes() {
	local env_id=$1
	local role=$2
	fuel nodes --env-id ${env_id} | awk -F\| '$7 ~ /'"$role"'/ && /^[0-9]+? +?\|/{gsub(" ", "", $5); print $5}'
} 

extract_ceph_conf() {
	sed -r 's/.*-c ([^ ]+).*/\1/g'
} 

check_env_exists $SOURCE_ENV_ID || { 
	echo "Env $SOURCE_ENV_ID not found"
	exit 1
} 

controller1=$(get_env_nodes $SOURCE_ENV_ID "controller" | head -1)

test -z "$controller1" && {
	echo "No controllers found in Env $SOURCE_ENV_ID"
	exit 1
} 

controller1_hostname=$(ssh $SSH_ARGS $controller1 hostname | cut -d. -f1)
controller1_db_path=/var/lib/ceph/mon/ceph-${controller1_hostname} 

ssh $SSH_ARGS $controller1 test -d $controller1_db_path  || {
  echo "$controller1_db_path not found at $controller1"
  exit 1
} 

ceph_args=$(ssh $SSH_ARGS $controller1 "pgrep 'ceph-mon' | xargs ps -fp | grep -m1 '^root '")

test -z "$ceph_args" && {
	echo "no ceph-mon process on $controller1"
	exit 1
} 

config_path=$(echo $ceph_args | extract_ceph_conf) 

test -z "$config_path" && {
	echo "Could not extract config_path from \'$ceph_args\'"
	exit 1
} 

# we assume, ceph keyrings must be placed in ceph.conf directory
ceph_conf_dir=$(dirname $config_path)


check_env_exists $DST_ENV_ID || { 
	echo "Env $DST_ENV_ID not found"
	exit 1
} 

dst_controllers=$(get_env_nodes $DST_ENV_ID "controller")

test -z "$dst_controllers" && {
	echo "No controllers found in Env $SOURCE_ENV_ID"
	exit 1
} 

dst_controllers_hostnames=$(echo -n $dst_controllers | xargs -I{} ssh $SSH_ARGS {} hostname | cut -d. -f1)
source_controllers=$(ssh $SSH_AGS $controller1 cat $config_path | awk -F= '$1 = /mon_host/ {print gensub("^ ", "", "", $2)}')

source_controllers_mask=$(echo ${source_controllers} | sed 's/ /|/g')

mon_initial_members=""
mon_hosts=""

# collect avialable dst controllers
for ctrl_host in ${dst_controllers}; do
	ip_match=`ssh $SSH_ARGS $ctrl_host ip addr | grep -m1 -E "${source_controllers_mask}" | sed -r 's/[ ]+?inet ([^\/]+).*/\1/'`
	test -z "$ip_match" && continue
	mon_initial_members="$mon_initial_members `ssh $SSH_ARGS $ctrl_host hostname | cut -d. -f1`"
	mon_hosts="$mon_hosts $ip_match"
done

DST_BASE_DIR="/"
for ctrl_host in ${mon_initial_members}; do
   ctrl_host_db_path="/var/lib/ceph/mon/ceph-${ctrl_host}"
   ssh $SSH_ARGS $ctrl_host "rm -rf /etc/ceph; mkdir /etc/ceph; test -d $ctrl_host_db_path && rm -rf $ctrl_host_db_path;  :"

   ssh $SSH_ARGS $controller1 "tar cvf - $ceph_conf_dir $controller1_db_path" | ssh $SSH_ARGS $ctrl_host "
	tar xvf - -C / && 
	set -e
	mv $controller1_db_path $ctrl_host_db_path
	sed -i'' 's/^mon_initial_members =.*/mon_initial_members =$mon_initial_members/g;
		  s/^mon_host =.*/mon_host =$mon_hosts/g;
		  s/^host =.*/host = ${ctrl_host}/g' $DST_BASE_DIR/${ceph_conf_dir}/ceph.conf 

	cat /etc/ceph/ceph.conf | awk -F= '
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
pssh -i -H "${mon_initial_members}" "/etc/init.d/ceph restart mon"
