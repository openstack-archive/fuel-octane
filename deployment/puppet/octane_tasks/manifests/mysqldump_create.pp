
# == Class: octane_tasks::mysqldump_restore
#
# It dumps, encrypts and compreses DB to a dump.
#
class octane_tasks::mysqldump_create {
  $nova_hash                  = hiera_hash('nova')
  $password                   = $nova_hash['db_password']
  $db_list_command            = 'mysql --silent --batch -e "show databases" | egrep -v "(Database|information_schema|performance_schema|mysql)" | tr "\n" " "'
  $compress_and_enc_command   = 'gzip | openssl enc -e -aes256 -pass env:PASSWORD -out /var/tmp/dbs.original.sql.gz.enc'

  exec { 'backup_and_encrypt':
    command     => "mysqldump --defaults-file=/root/.my.cnf --host localhost --add-drop-database --lock-all-tables --databases ${db_list_command} | ${compress_and_enc_command}",
    provider    => shell,
    environment => "PASSWORD=${password}",
  }
}
