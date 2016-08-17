# == Class: octane_tasks::mysqldump_restore
#
# It decrypts, decompreses and restores DB dump.
#
class octane_tasks::mysqldump_restore {
  $nova_hash = hiera_hash('nova')
  $password  = $nova_hash['db_password']

  # `set -e pipefail` is required not to supress an error if provided input dump file is corrupted
  exec { 'decrypt_and_restore':
    command     => 'set -o pipefail; openssl enc -d -aes256 -pass env:PASSWORD -in /var/tmp/dbs.original.sql.gz.enc | gzip -d | mysql --defaults-file=/root/.my.cnf',
    provider    => shell,
    environment => "PASSWORD=${password}",
  }
}
