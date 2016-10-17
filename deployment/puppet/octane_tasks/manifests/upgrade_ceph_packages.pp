# == class: octane_tasks::upgrade_ceph_packages
#
# this class upgrades ceph packages on the current node
#
class octane_tasks::upgrade_ceph_packages {
  $ceph_mon_versions = ceph_get_version('mon')
  $ceph_osd_versions = ceph_get_version('osd')

  $ceph_release = hiera('ceph_upgrade_release')
  $node_hostnames_string = join(hiera('ceph_upgrade_hostnames'), " ")

  Exec {
    provider => shell,
  }

  if ! ceph_equal_versions($ceph_mon_versions, $ceph_osd_versions) {

    exec { 'upgrade-ceph-packages':
      command => "ceph-deploy install --release ${ceph_release} ${node_hostnames_string}",
    }

  } else {
    notice('the version of osd on current node matches mon version, nothing to upgrade.')
  }
}

