$upgrade_config = hiera_hash('upgrade', {})
$db_upgrade_config = pick($upgrade_config['db'], {})
$corosync_services_to_stop = $upgrade_config['corosync_services_to_stop']
$generic_services_to_stop = $upgrade_config['generic_services_to_stop']
$default_corosync_service_hash = {ensure => "stopped", provider=>"pacemaker"}
$default_generic_service_hash = {ensure => "stopped"}
$corosync_services_to_stop = merge($default_generic_service_hash, $corosync_services_to_stop)
ensure_resource('service', $corosync_services_to_stop)
ensure_resource('service', $generic_services_to_stop)