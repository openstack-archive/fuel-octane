#!/bin/bash -ex
# Config-ish
MAGNET_511_ISO='magnet:?xt=urn:btih:63907abc2acf276d595cd12f9723088fd66cbe24&dn=MirantisOpenStack-5.1.1.iso&tr=http%3A%2F%2Ftracker01-bud.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Ftracker01-msk.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Ftracker01-mnv.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Fseed-qa.msk.mirantis.net%3A8080%2Fannounce&ws=http%3A%2F%2Ffuel-storage.srt.mirantis.net%2Ffuelweb%2FMirantisOpenStack-5.1.1.iso'
MAGNET_60_LRZ='magnet:?xt=urn:btih:d8bda80a9079e1fc0c598bc71ed64376103f2c4f&dn=MirantisOpenStack-6.0-upgrade.tar.lrz&tr=http%3A%2F%2Ftracker01-bud.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Ftracker01-msk.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Ftracker01-mnv.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Fseed-qa.msk.mirantis.net%3A8080%2Fannounce&ws=http%3A%2F%2Ffuel-storage.srt.mirantis.net%2Ffuelweb%2FMirantisOpenStack-6.0-upgrade.tar.lrz'
MAGNET_61_LRZ='magnet:?xt=urn:btih:baf78dcbffae42cfb5226c6b1d94b079035a74af&dn=MirantisOpenStack-6.1-upgrade.tar.lrz&tr=http%3A%2F%2Ftracker01-bud.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Ftracker01-mnv.infra.mirantis.net%3A8080%2Fannounce&tr=http%3A%2F%2Ftracker01-msk.infra.mirantis.net%3A8080%2Fannounce&ws=http%3A%2F%2Fvault.infra.mirantis.net%2FMirantisOpenStack-6.1-upgrade.tar.lrz'
DOWNLOAD_TORRENTS="$MAGNET_511_ISO $MAGNET_60_LRZ $MAGNET_61_LRZ"
FUEL_ISO='MirantisOpenStack-5.1.1.iso'

MYDIR="$(readlink -e "$(dirname "$BASH_SOURCE")")"
# Use provided preseed.cfg to install everything

# Transmission
DOWNLOADS_DIR="$HOME/Downloads"
mkdir -p "$DOWNLOADS_DIR"
setfacl -m 'user:debian-transmission:rwx' "$DOWNLOADS_DIR"
sudo apt-get install transmission-cli transmission-daemon
sudo service transmission-daemon stop
EDIT_SCRIPT='import sys,json; i=iter(sys.argv); next(i); fname=next(i); s=json.load(open(fname)); s.update(zip(i,i)); json.dump(s,open(fname,"w"),indent=4,sort_keys=True)' 
sudo python -c "$EDIT_SCRIPT" /etc/transmission-daemon/settings.json download-dir "$DOWNLOADS_DIR"
sudo service transmission-daemon start
alias tr='transmission-remote -n transmission:transmission'
for magnet in $DOWNLOAD_TORRENTS; do
    transmission-remote -n transmission:transmission -a "$magnet"
done

# Libvirt
# Fucking https://bugs.launchpad.net/ubuntu/+source/libvirt/+bug/1343245
printf '  /dev/zvol/vms/* rw,\n  /dev/zd* rw,\n' | sudo tee -a /etc/apparmor.d/abstractions/libvirt-qemu > /dev/null
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

# Don't let LVM find zvols
sudo sed -i 's#.*global_filter =.*#    global_filter = [ "r|^/dev/zd.*|", "r|^/dev/zvol/.*|" ]#' /etc/lvm/lvm.conf

# Master node
while [ ! -f "$DOWNLOADS_DIR/$FUEL_ISO" ]; do
  sleep 10
done
virsh vol-create-as vms fuel 100G
virsh define <(sed "s|%ISO%|$DOWNLOADS_DIR/$FUEL_ISO|" "$MYDIR/fuel.xml")
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
