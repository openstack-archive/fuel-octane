#!/bin/bash -ex
# In debian-installer's shell run:
# anna-install network-console
# it'll bring up password settings and SSH setup after network setup
# BTW, 172.18.184.58:3142 is a good choice for mirror in cz ;)

# After system is booted
sudo apt-get install libvirt-bin qemu-kvm lvm2
# Logout/login to get into libvirtd group
# Fucking https://bugs.launchpad.net/ubuntu/+source/libvirt/+bug/1343245
printf '  /dev/vms/* rw,\n  /dev/dm-* rw,\n' | sudo tee -a /etc/apparmor.d/abstractions/libvirt-qemu > /dev/null
# Setup LVM
virsh pool-define-as vms logical --source-dev /dev/sdc
virsh pool-build vms
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
cat > fuel.xml <<EOF
<domain type='kvm'>
  <name>fuel</name>
  <memory>4194304</memory>
  <vcpu>2</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='cdrom'/>
    <boot dev='hd'/>
  </os>
  <features><acpi/><apic/><pae/></features>
  <on_reboot>destroy</on_reboot>
  <devices>
    <disk type='volume'>
      <source pool='vms' volume='fuel'/>
      <target dev='hda'/>
    </disk>
    <disk type='file' device='cdrom'>
      <source file='/home/ubuntu/MirantisOpenStack-5.1.1.iso'/>
      <target dev='hdb'/>
      <address type='drive' bus='1'/>
    </disk>
    <interface type='network'>
      <source network='admin'/>
      <model type='e1000'/>
    </interface>
    <graphics type='vnc' listen='0.0.0.0' autoport='yes'/>
    <memballoon model='virtio'/>
  </devices>
</domain>
EOF
virsh vol-create-as vms fuel 100G
virsh define fuel.xml
virsh start fuel
virsh event fuel lifecycle  # wait for shutdown on reboot
virsh event fuel lifecycle --timeout 5  # wait for final shutdown on reboot
# This error is OK: (see https://www.redhat.com/archives/libvir-list/2015-April/msg00619.html)
# error: inter machine='q35'nal error: virsh event: no domain VSH_OT_DATA option
EDITOR="sed -i '/boot.*cdrom/d; /on_reboot/d'" virsh edit fuel  # don't boot from CD, don't destroy on reboot
virsh start fuel
virsh autostart fuel
sleep 600  # let it install everything

# Other nodes
cat > node.xml <<EOF
<domain type='kvm'>
  <name>%NAME%</name>
  <memory unit='GiB'>%MEMORY%</memory>
  <vcpu>%CPU%</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
  </os>
  <features><acpi/><apic/><pae/></features>
  <devices>
    <disk type='volume'><source pool='vms' volume='%NAME%'/><target dev='hda'/></disk>
    <disk type='volume'><source pool='vms' volume='%NAME%-ceph'/><target dev='hdb'/><address type='drive' bus='1'/></disk>
    <interface type='network'><source network='admin'/><model type='e1000'/><boot order='1'/></interface>
    <interface type='network'><source network='management'/><model type='e1000'/></interface>
    <interface type='network'><source network='private'/><model type='e1000'/></interface>
    <interface type='network'><source network='public'/><model type='e1000'/></interface>
    <interface type='network'><source network='storage'/><model type='e1000'/></interface>
    <graphics type='vnc' listen='0.0.0.0' autoport='yes'/>
    <memballoon model='virtio'/>
  </devices>
</domain>
EOF

for i in $(seq 1 6); do
  name="controller-$i"
  virsh vol-create-as vms $name 100G
  virsh define <(sed "s/%NAME%/$name/; s/%CPU%/2/; s/%MEMORY%/4/; /-ceph/d" node.xml)
  virsh autostart $name
  virsh start $name
  sleep 120
done
for i in $(seq 1 6); do
  name="compute-$i"
  virsh vol-create-as vms $name 100G
  virsh vol-create-as vms $name-ceph 100G
  virsh define <(sed "s/%NAME%/$name/; s/%CPU%/4/; s/%MEMORY%/8/" node.xml)
  virsh autostart $name
  virsh start $name
  sleep 120
done
