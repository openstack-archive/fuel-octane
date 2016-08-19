# == Class: octane_tasks::ceph_mon_start
#
class octane_tasks::ceph_mon_stop {
  service { 'ceph-mon-all': ensure => stopped }
}
