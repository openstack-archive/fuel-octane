#!/bin/bash

set -x

modulespath="/etc/puppet/2014.2-6.0/modules"
astutepath="/usr/lib64/ruby/gems/2.1.0/gems/astute-6.0.0/lib/astute/"
upload_cirros_image_path="$astutepath/post_deployment_actions/upload_cirros_image.rb"

sed -ie "s%skip_existing = false%skip_existing = true%" \
    $modulespath/l23network/manifests/l2/bridge.pp
sed -ie "s%defaultto(false)%defaultto(true)%" \
    $modulespath/l23network/lib/puppet/type/l2_ovs_bridge.rb
sed -ie "s%(\$run_ping_checker) = .*$%\1 = false%" \
    $modulepath/osnailyfacter/mainfests/cluster_ha.pp

dockerctl shell astute sed -i "90s%^%#%" $upload_cirros_image_path
dockerctl shell astute sed -i "90i\ \ \ \ \ \ \ \ response['data']['exit_code'] = 0" \
    $upload_cirros_image_path
