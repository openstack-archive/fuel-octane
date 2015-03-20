# prepare and bring online the devices listed in $::ceph::osd_devices
class ceph::osd (
  $osd_devices=$::ceph::osd_devices,
){
  firewall {'011 ceph-osd allow':
    chain   => 'INPUT',
    dport   => '6800-7100',
    proto   => 'tcp',
    action  => accept,
  }

  $osd_prepare_devices = split($osd_devices[0], ' ')
  $osd_activate_devices = split($osd_devices[1], ' ')
  $prepare_devices = join(prefix($osd_prepare_devices, "${::hostname}:"), ' ')
  $activate_devices = join(prefix($osd_activate_devices, "${::hostname}:"), ' ')

  if ! empty($prepare_devices) {
    exec { 'ceph-deploy osd prepare':
      # ceph-deploy osd prepare is ensuring there is a filesystem on the
      # disk according to the args passed to ceph.conf (above).
      #
      # It has a long timeout because of the format taking forever. A
      # resonable amount of time would be around 300 times the length of
      # $osd_nodes. Right now its 0 to prevent puppet from aborting it.

      command   => "ceph-deploy osd prepare ${prepare_devices}",
      returns   => 0,
      timeout   => 0, # TODO: make this something reasonable
      tries     => 2, # This is necessary because of race for mon creating keys
      try_sleep => 1,
      logoutput => true,
      unless    => "grep -q '^${ osd_prepare_devices[0] }' /proc/mounts",
    }
    Firewall['011 ceph-osd allow'] ->
    Exec['ceph-deploy osd prepare']
  }

  if ! empty($activate_devices) {
    exec { 'ceph-deploy osd activate':
      command   => "ceph-deploy osd activate ${activate_devices}",
      returns   => 0,
      logoutput => true,
    }
    Firewall['011 ceph-osd allow'] ->
    Exec['ceph-deploy osd activate']
  }

  if ! (empty($prepare_devices) or empty($activate_devices)) {
    Exec['ceph-deploy osd prepare'] ->
    Exec['ceph-deploy osd activate']
  }
}
