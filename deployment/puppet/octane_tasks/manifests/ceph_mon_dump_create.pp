
class octane_tasks::ceph_mon_dump_create {
  exec { 'ceph_mon_create':
    command => "tar -czPf /tmp/ceph_mon.tar.gz /var/lib/ceph/mon/ceph-${::hostname}",
  }
}
