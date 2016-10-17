# == Class: octane_tasks::unset_noout
#
# This class unsets the noout flag for OSD pre-upgrade
#
class octane_tasks::unset_noout {

  Exec {
    provider => shell,
  }

  exec { 'unset-noout-flag':
    command => 'ceph osd unset noout',
    onlyif  => 'ceph -s | grep -q "noout flag.\+ set"',
  }

}
