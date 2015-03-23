#!/bin/sh -ex
PATCH_DIR=../patches/puppet
cd $PATCH_DIR
cp ./ceph_osd.rb /etc/puppet/2014.2-6.0/modules/ceph/lib/facter/ceph_osd.rb
cp ./init.pp /etc/puppet/2014.2-6.0/modules/ceph/manifests/init.pp
cp ./osd.pp /etc/puppet/2014.2-6.0/modules/ceph/manifests/osd.pp
