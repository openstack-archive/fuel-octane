
class octane_tasks::ceph_mon_dump_create {
  exec { 'ceph_mon_create':
    command     => "tar -czPf /var/tmp/ceph_mon.tar.gz --exclude ceph.conf * /etc/ceph",
    provider    => shell,
    cwd         => "/var/lib/ceph/mon/ceph-${::hostname}",
  }
}
