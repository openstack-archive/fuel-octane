#!/bin/sh -ex
cp ./ceph_osd.rb /etc/puppet/modules/ceph/lib/facter/ceph_osd.rb
cp ./init.pp /etc/puppet/modules/ceph/manifests/init.pp
cp ./osd.pp /etc/puppet/modules/ceph/manifests/osd.pp
