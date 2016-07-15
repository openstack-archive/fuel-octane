$upgrade_hash = hiera('upgrade')
$databases = hiera($upgrade_hash['databases'])
restore_mysqlbases {'all': databases=>$databases}