# == class: octane_tasks::upgrade_ceph_packages
#
# this class upgrades ceph packages on the current node
#
class octane_tasks::upgrade_ceph_packages {
  $ceph_mon_ids = ceph_get_mon_ids()
  $ceph_mon_version = ceph_get_version('mon', $ceph_mon_ids)
  $ceph_osd_ids = ceph_get_osd_ids($::hostname)
  $ceph_osd_version = ceph_get_version('osd', $ceph_osd_ids)

  $ceph_release = hiera('ceph_upgrade_release')

  Exec {
    provider => shell,
  }

  if $ceph_mon_version != $ceph_osd_version {

    exec { 'upgrade-ceph-packages':
      command => "ceph-deploy install --release ${ceph_release} ${::hostname}",
    }

  } else {
    notice('the version of osd on current node matches mon version, nothing to upgrade.')
  }
}

