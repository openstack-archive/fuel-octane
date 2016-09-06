
# == Class:octane_tasks::ceph_reconfiguration
#
# It replaces fsid by former fsid, using taken from the original controller ceph.conf, in:
#   - ceph.conf
#   - Ceph Monmap
#
class octane_tasks::ceph_reconfiguration {
  Exec {
    provider => shell,
  }

  $orig_fsid    = ceph_get_fsid('/var/tmp/ceph.conf')
  $tmp_mon_map  = '/var/tmp/ceph_mon_map'

  validate_re($orig_fsid, '\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z')

  exec { 'extract_map':
    command => "ceph-mon -i ${::hostname} --extract-monmap ${tmp_mon_map}",
  }

  exec { 'delete_old_mon_db':
    command => "rm -rf /var/lib/ceph/mon/ceph-${::hostname}/*",
    require => Exec['extract_map'],
  }

  exec { 'extract_db':
    command => 'tar -xzPf /var/tmp/ceph_mon.tar.gz',
    cwd     => "/var/lib/ceph/mon/ceph-${::hostname}",
    require => Exec['delete_old_mon_db'],
  }

  exec { 'extract_ceph_etc':
    command => 'tar -xzPf /var/tmp/ceph_etc.tar.gz',
  }

  augeas { 'ceph.conf':
    lens      => 'Ceph.lns',
    incl      => '/etc/ceph/ceph.conf',
    load_path => '/usr/share/augeas/lenses:/etc/fuel/octane/puppet/octane_tasks/lib/augeas/lenses',
    changes   => [
      "set /files/etc/ceph/ceph.conf/global/fsid ${orig_fsid}",
    ]
  }

  exec { 'change_fsid':
    command => "monmaptool --fsid ${orig_fsid} --clobber ${tmp_mon_map}",
    require => Exec['extract_map'],
  }

  exec { 'inject_map':
    command => "ceph-mon -i ${::hostname} --inject-monmap ${tmp_mon_map}",
    require => [
      Exec['change_fsid'],
      Augeas['ceph.conf'],
    ],
  }
}

