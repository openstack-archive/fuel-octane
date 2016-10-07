# == class: octane_tasks::restart_ceph_osd
#
# this class restarts ceph osd after package upgrade
#
class octane_tasks::restart_ceph_osd {
  $ceph_mon_ids = ceph_get_mon_ids()
  $ceph_mon_version = ceph_get_version('mon', $ceph_mon_ids)
  $ceph_osd_ids = ceph_get_osd_ids($::hostname)
  $ceph_osd_version = ceph_get_version('osd', $ceph_osd_ids)

  Exec {
    provider => shell,
  }

  if $ceph_mon_version != $ceph_osd_version {

    exec { 'restart-ceph-osd':
      command => 'restart ceph-osd-all',
    }

  } else {
    notice('the version of osd on current node matches mon version, nothing to upgrade.')
  }
}
