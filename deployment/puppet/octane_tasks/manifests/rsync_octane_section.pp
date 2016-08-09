
# == Class: octane_tasks::rsync_octane_section
#
# This class adds a section to rsyncd.conf for Octane with r/w support.
# It also restarts Rsyncd if it's necessary.
#
class octane_tasks::rsync_octane_section {
  augeas { 'rsync_octane_section' :
    context => '/files/etc/rsyncd.conf/octane',
    notify  => Service['rsyncd'],
    changes => [
      'set path /var/www/nailgun/octane',
      'set read\ only false',
      'set uid 0',
      'set gid 0',
      'set use\ chroot no',
    ]
  }

  service { 'rsyncd': }
}
