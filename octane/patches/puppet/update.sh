#!/bin/sh -ex
PATCH_DIR=$(dirname $0)
cp $PATCH_DIR/ceph_osd.rb /etc/puppet/2014.2-6.0/modules/ceph/lib/facter/ceph_osd.rb
cp $PATCH_DIR/init.pp /etc/puppet/2014.2-6.0/modules/ceph/manifests/init.pp
cp $PATCH_DIR/osd.pp /etc/puppet/2014.2-6.0/modules/ceph/manifests/osd.pp
