class octane_tasks::maintenance (
  $ensure_cluster_services = nil,
  $ensure_init_services    = nil,
  $cluster_services_list   = $octane_tasks::params::cluster_services_list,
  $init_services_list      = $octane_tasks::params::init_services_list,
) inherits octane_tasks::params {

  # Manage init services
  case $ensure_init_services {
    'running', 'stopped', true, false: {

      ensure_resource(
        'service',
        $init_services_list,
        {'ensure' => $ensure_init_services}
      )
    }

    default: {
      notice("\$ensure_init_services is set to $ensure_init_services, skipping")
    }
  }

  # Manage cluster services
  case $ensure_cluster_services {
    'running', 'stopped', true, false: {

      ensure_resource(
        'service',
         $cluster_services_list,
         {'ensure' => $ensure_cluster_services, provider => 'pacemaker'}
      )
    }
    default: {
      notice("\$ensure_cluster_services is set to $ensure_cluster_services, skipping")
    }
  }
}
