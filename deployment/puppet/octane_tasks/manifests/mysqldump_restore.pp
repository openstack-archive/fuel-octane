
# TODO(pchechetin): Add extensive desription for class
class octane_tasks::mysqldump_restore {
  $nova_hash = hiera_hash('nova')
  $password  = $nova_hash['db_password']

  exec { 'decrypt_and_restore':
    command     => 'openssl enc -d -aes256 -pass env:PASSWORD -in /var/tmp/dbs.original.sql.gz.enc | gzip -d | mysql --defaults-file=/root/.my.cnf',
    provider    => shell,
    environment => "PASSWORD=${password}",
  }
}
