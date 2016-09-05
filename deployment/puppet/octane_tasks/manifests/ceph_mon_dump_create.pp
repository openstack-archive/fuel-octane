# == Class: octane_tasks::ceph_mon_dump_create
#
# It creates a dump of Ceph Monitor database.
#
class octane_tasks::ceph_mon_dump_create {

  Exec {
    provider => shell,
  }

  exec { 'ceph_mon_dump_create':
    command => 'tar -czPf /var/tmp/ceph_mon.tar.gz --exclude ceph.conf *',
    cwd     => "/var/lib/ceph/mon/ceph-${::hostname}",
  }

  exec { 'ceph_etc_dump_create':
    command  => 'tar -czPf /var/tmp/ceph_etc.tar.gz /etc/ceph',
  }

}
