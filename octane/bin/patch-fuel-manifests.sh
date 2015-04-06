#!/bin/bash

PATCH_DIR=../patches/

patchfile() {
    [ -z "$1" ] && die "No original file provided, exiting"
    [ -z "$2" ] && die "No patch file provided, exiting"
    patch -Np1 --dry-run --silent $1 $2 2>/dev/null && patch -Np1 $1 $2
}

set -x

modulespath="/etc/puppet/2014.2-6.0/modules"
astutepath="/usr/lib64/ruby/gems/2.1.0/gems/astute-6.0.0/lib/astute/"
deploy_actions_path="$astutepath/deploy_actions.rb"

sed -ie "s%skip_existing = false%skip_existing = true%" \
    $modulespath/l23network/manifests/l2/bridge.pp
sed -ie "s%defaultto(false)%defaultto(true)%" \
    $modulespath/l23network/lib/puppet/type/l2_ovs_bridge.rb

dockerctl shell astute sed -i "94s%^%#%" $deploy_actions_path
dockerctl shell astute supervisorctl restart astute

cd $PATCH_DIR
patchfile $modulespath/openstack/manifests/controller.pp ./controller.pp.patch
