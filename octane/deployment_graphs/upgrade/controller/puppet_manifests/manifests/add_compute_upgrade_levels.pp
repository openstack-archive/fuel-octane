
$compute_config = hiera_hash("compute", {})
$version = $compute_config['upgrade_level']

if $version {
  nova_config {"upgrade_values/compute": value => $version}
}
$services_list = []
ensure_resource("nova::generic_service", $services_list)
Nova_config <||> ~> Service <| tag=='nova-service' |>