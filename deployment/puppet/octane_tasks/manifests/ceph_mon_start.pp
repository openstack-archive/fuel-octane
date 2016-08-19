# == Class: octane_tasks::ceph_mon_start
#
class octane_tasks::ceph_mon_start {
  service { 'ceph-mon-all': ensure => running }
}
