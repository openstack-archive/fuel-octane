# == class: octane_tasks::restart_ceph_osd
#
# this class restarts ceph osd after package upgrade
#
class octane_tasks::restart_ceph_osd {
  $ceph_mon_versions = ceph_get_version('mon')
  $ceph_osd_versions = ceph_get_version('osd')

  Exec {
    provider => shell,
  }

  if ! ceph_equal_versions($ceph_mon_versions, $ceph_osd_versions) {

    exec { 'restart-ceph-osd':
      command => 'restart ceph-osd-all',
    }

  } else {
    notice('the version of osd on current node matches mon version, nothing to upgrade.')
  }
}
