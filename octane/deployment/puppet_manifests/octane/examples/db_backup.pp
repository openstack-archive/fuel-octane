$databases = hiera($upgrade_hash['databases'])
dump_mysqlbases {'all': databases=>$databases}