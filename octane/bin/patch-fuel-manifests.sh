#!/bin/bash

set -x

modulespath="/etc/puppet/2014.2-6.0/modules"

sed -ie "s%skip_existing = false%skip_existing = true%" \
    $modulespath/l23network/manifests/l2/bridge.pp
sed -ie "s%defaultto(false)%defaultto(true)%" \
    $modulespath/l23network/lib/puppet/type/l2_ovs_bridge.rb
sed -ie "s%(\$run_ping_checker) = .*$%\1 = false%" \
    $modulepath/osnailyfacter/mainfests/cluster_ha.pp
