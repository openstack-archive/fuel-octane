#!/bin/bash -ex
MYDIR="$(readlink -e "$(dirname "$BASH_SOURCE")")"
# Use provided preseed.cfg to install everything
# Fucking https://bugs.launchpad.net/ubuntu/+source/libvirt/+bug/1343245
printf '  /dev/vms/* rw,\n  /dev/dm-* rw,\n' | sudo tee -a /etc/apparmor.d/abstractions/libvirt-qemu > /dev/null
# Build and install Libvirt package with ZFS support
mkdir ~/libvirt-build
pushd ~/libvirt-build
apt-get source libvirt-bin
sudo apt-get build-dep libvirt-bin
sudo apt-get install devscripts
cd libvirt-1.2.12
patch -p0 < "$MYDIR/libvirt.patch"
debuild -uc -us -b
cd ..
sudo dpkg -i --force-confnew libvirt0_1.2.12-0ubuntu13_amd64.deb libvirt-bin_1.2.12-0ubuntu13_amd64.deb
popd
# Setup ZFS pool
virsh pool-define-as vms zfs --source-name vms
# no pool-build since we need -f flag for zpool create
sudo zpool create -f vms /dev/sdc
virsh pool-autostart vms
virsh pool-start vms

# Networks
virsh net-undefine default
for net in admin management private public storage; do
  if [ "$net" = "admin" ]; then
    fwd="<ip address='172.20.0.1' prefix='24'></ip>"
  elif [ "$net" = "public" ]; then
    fwd="<forward mode='nat'/><ip address='172.16.0.1' prefix='24'></ip>"
  else
    fwd=""
  fi
  virsh net-define <(echo "<network><name>$net</name>$fwd</network>")
  virsh net-autostart $net
  virsh net-start $net
done

# Master node
# Download ISO from some node
virsh vol-create-as vms fuel 100G
virsh define "$MYDIR/fuel.xml"
virsh start fuel
virsh event fuel lifecycle  # wait for shutdown on reboot
virsh event fuel lifecycle --timeout 5  # wait for final shutdown on reboot
# This error is OK: (see https://www.redhat.com/archives/libvir-list/2015-April/msg00619.html)
# error: internal error: virsh event: no domain VSH_OT_DATA option
EDITOR="sed -i '/boot.*cdrom/d; /on_reboot/d'" virsh edit fuel  # don't boot from CD, don't destroy on reboot
virsh start fuel
virsh autostart fuel
sleep 600  # let it install everything

# Other nodes
for i in $(seq 1 6); do
  name="controller-$i"
  virsh vol-create-as vms $name 100G
  virsh define <(sed "s/%NAME%/$name/; s/%CPU%/2/; s/%MEMORY%/4/; /-ceph/d" "$MYDIR/node.xml")
  virsh autostart $name
  virsh start $name
  sleep 120
done
for i in $(seq 1 6); do
  name="compute-$i"
  virsh vol-create-as vms $name 100G
  virsh vol-create-as vms $name-ceph 100G
  virsh define <(sed "s/%NAME%/$name/; s/%CPU%/4/; s/%MEMORY%/8/" "$MYDIR/node.xml")
  virsh autostart $name
  virsh start $name
  sleep 120
done
