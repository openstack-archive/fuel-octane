# == class: octane_tasks::set_noout
#
# this class sets the noout flag for osd pre-upgrade
#
class octane_tasks::set_noout {
  $ceph_mon_ids = ceph_get_mon_ids()
  $ceph_mon_version = ceph_get_version('mon', $ceph_mon_ids)
  $ceph_osd_ids = ceph_get_osd_ids($::hostname)
  $ceph_osd_version = ceph_get_version('osd', $ceph_osd_ids)

  Exec {
    provider => shell,
  }

  if $ceph_mon_version != $ceph_osd_version {

    exec { 'set-noout-flag':
      command => 'ceph osd set noout',
      unless  => 'ceph -s | grep -q "noout flag.\+ set"',
    }

  } else {
    notice('the version of osd on current node matches mon version, nothing to upgrade.')
  }
}
