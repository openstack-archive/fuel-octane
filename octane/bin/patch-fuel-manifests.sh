#!/bin/bash

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

patch -Np1 $modulespath/openstack/manifests/controller.pp ./controller.pp.patch || :
