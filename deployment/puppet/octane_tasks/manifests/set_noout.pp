# == class: octane_tasks::set_noout
#
# this class sets the noout flag for osd pre-upgrade
#
class octane_tasks::set_noout {
  $ceph_mon_versions = ceph_get_version('mon')
  $ceph_osd_versions = ceph_get_version('osd')

  Exec {
    provider => shell,
  }

  if ! ceph_equal_versions($ceph_mon_versions, $ceph_osd_versions) {

    exec { 'set-noout-flag':
      command => 'ceph osd set noout',
      unless  => 'ceph -s | grep -q "noout flag.\+ set"',
    }

  } else {
    notice('the version of osd on current node matches mon version, nothing to upgrade.')
  }
}
