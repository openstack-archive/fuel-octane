
# == Class: octane_tasks::rsync_octane_section
#
# This class adds two section to rsyncd.conf for Octane:
#   Code with with ready only access.
#   Data with read and write access.
class octane_tasks::rsync_octane_section {
  augeas { 'rsync_octane_section_code':
    context => '/files/etc/rsyncd.conf/octane_code',
    changes => [
      'set path /var/www/nailgun/octane_code',
      'set read\ only true',
      'set uid 0',
      'set gid 0',
      'set use\ chroot no',
    ]
  }

  augeas { 'rsync_octane_section_data':
    context => '/files/etc/rsyncd.conf/octane_data',
    changes => [
      'set path /var/www/nailgun/octane_data',
      'set read\ only false',
      'set use\ chroot no',
    ]
  }

  $admin_network = hiera_hash('ADMIN_NETWORK')
  $admin_ip      = $admin_network['ipaddress']

  augeas { 'xinetd_rsync':
    context => '/files/etc/xinetd.d/rsync/service',
    notify  => Service['xinetd'],
    changes => [
      "set bind ${admin_ip}",
    ]
  }

  service { 'xinetd': }
}
