$upgrade_config = hiera_hash('upgrade', {})
$db_upgrade_config = pick($upgrade_config['db'], {})
$corosync_services_to_stop_list = $upgrade_config['corosync_services_to_stop']
$generic_services_to_stop_list = $upgrade_config['generic_services_to_stop']
$default_corosync_service_hash = {ensure => "stopped", provider=>"pacemaker"}
$default_generic_service_hash = {ensure => "stopped"}
$corosync_services_to_stop_hash = array_to_hash($corosync_services_to_stop_list, $default_corosync_service_hash)
$generic_services_to_stop_hash = array_to_hash($corosync_services_to_stop_list, $default_generic_service_hash)
ensure_resource('service', $corosync_services_to_stop_hash)
ensure_resource('service', $generic_services_to_stop_hash)
