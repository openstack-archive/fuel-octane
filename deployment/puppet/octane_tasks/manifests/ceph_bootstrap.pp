
class octane_tasks::ceph_bootstrap {
  Exec {
    provider => shell,
  }

  exec { 'ceph.auth.import':
    command => 'ceph auth import -i /root/ceph.bootstrap-osd.keyring',
  }

  exec { 'ceph.auth.caps':
    command => 'ceph auth caps client.bootstrap-osd mon allow profile bootstrap-osd',
    require => Exec['ceph.auth.import'],
  }
}
