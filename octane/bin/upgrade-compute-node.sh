#!/bin/sh -e
extract_vars() {
        sed -re '/^\+.*%.*/ s/.*%([^%]+)%.*/\L\1/;tx;d;:x' $PATCH
}

convert_vars_to_regex() {
        tr "\n" " "| sed -re 's,^,^(,;s,.$,),;s, ,|,g'
}

generate_template_regex() {
        ssh root@$1 find /etc/neutron -type f -exec cat {} \;| egrep "`extract_vars | convert_vars_to_regex`" {}  | awk -F= '{key = gensub(" ", "", "g", $1); printf("s|%%%s%%|%s|g;", toupper(key), $2)}'
}

upgrade_compute_service() {
	local regex
	regex=$(generate_template_regex $1)
	sed -r "$regex" ${PATCH}  | ssh root@$1 "tee /tmp/patch-neutron-config_$1.patch"
	ssh root@$1 "apt-get update; apt-get install -o Dpkg::Options::='--force-confnew' --yes nova-compute"
	ssh root@$1 "cd /etc/neutron && patch -p0 < /tmp/patch-neutron-config_$1.patch"
}

add_apt_sources() {
	local source
	source="http://$(grep fuel /etc/hosts | cut -d \  -f1):8080/2014.2-6.0/ubuntu/x86_64"
	printf "\ndeb $source precise main\n" | ssh root@$1 "cat >> /etc/apt/sources.list"
}

PATCH=${2-"../patches/neutron-upgrade.patch"}

if [ ! -f "$PATCH" ]; then
    echo "Usage $0 neutron-upgrade.patch > neutron-upgrade-rendered.patch" >> /dev/stderr
    exit 1
fi

[ -f "./functions" ] && . ./functions

[ -z "$1" ] && die "No node ID provided, exiting"
add_apt_sources $1
upgrade_compute_service $1
