# == Class: octane_tasks::mysqldump_restore
#
# It decrypts, decompreses and restores DB dump.
#
class octane_tasks::mysqldump_restore inherits octane_tasks::params {
  $password  = $nova_hash['db_password']

  $dump_path        = '/var/tmp/dbs.original.sql.gz.enc'
  $restore_command  = "openssl enc -d -aes256 -pass env:PASSWORD -in ${dump_path} | gzip -d | mysql --defaults-file=/root/.my.cnf"

  exec { 'decrypt_and_restore':
    command     => $restore_command,
    environment => "PASSWORD=${password}",
    provider    => bash,
  }
}
