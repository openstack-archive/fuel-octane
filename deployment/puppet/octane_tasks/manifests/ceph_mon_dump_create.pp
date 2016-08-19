# == Class: octane_tasks::ceph_mon_dump_create
#
# It creates a dump of Ceph Monitor database.
#
class octane_tasks::ceph_mon_dump_create {

  # Create an archive of two dirs: /var/lib/ceph/mon/ceph-${node_id} and /etc/ceph(w/o ceph.conf)
  exec { 'ceph_mon_dump_create':
    command  => 'tar -czPf /var/tmp/ceph_mon.tar.gz --exclude ceph.conf * /etc/ceph',
    cwd      => "/var/lib/ceph/mon/ceph-${::hostname}",
    provider => shell,
  }
}
