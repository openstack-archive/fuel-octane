
# == Class: octane_tasks::mysqldump_create
#
# It dumps, encrypts and compreses DB to a dump.
#
class octane_tasks::mysqldump_create inherits octane_tasks::params {
  $password                   = $octane_tasks::params::nova_hash['db_password']
  $compress_and_enc_command   = 'gzip | openssl enc -e -aes256 -pass env:PASSWORD -out /var/tmp/dbs.original.sql.gz.enc'
  $mysql_args                 = '--defaults-file=/root/.my.cnf --host localhost --add-drop-database --lock-all-tables'

  $os_base_dbs = ['cinder', 'glance', 'heat', 'keystone', 'neutron', 'nova']

  if $octane_tasks::params::sahara_enabled {
    $sahara_db = ['sahara']
  } else {
    $sahara_db = []
  }

  if $octane_tasks::params::murano_enabled {
    $murano_db = ['murano']
  } else {
    $murano_db = []
  }

  if $octane_tasks::params::ironic_enabled {
    $ironic_db = ['ironic']
  } else {
    $ironic_db = []
  }

  $db_list = join(concat($os_base_dbs, $sahara_db, $murano_db, $ironic_db), ' ')

  exec { 'backup_and_encrypt':
    command     => "mysqldump ${mysql_args} --databases ${db_list} | ${compress_and_enc_command}",
    environment => "PASSWORD=${password}",
    provider    => bash,
  }
}
