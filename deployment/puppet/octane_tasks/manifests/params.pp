# == Class: octane_tasks::params
#
# This class contains paramaters for octane_tasks
#
class octane_tasks::params (
) {
  $nova_hash        = hiera_hash('nova')
  $ceilometer_hash  = hiera_hash('ceilometer', {'enabled' => false})
  $sahara_hash      = hiera_hash('sahara', {'enabled' => false})
  $murano_hash      = hiera_hash('murano', {'enabled' => false})
  $storage_hash     = hiera_hash('storage', {})
  $fuel_version     = hiera('fuel_version', '9.0')

  $ceilometer_enabled  = $ceilometer_hash['enabled']
  $sahara_enabled      = $sahara_hash['enabled']
  $murano_enabled      = $murano_hash['enabled']
  $cinder_vol_on_ctrl  = $storage_hash['volumes_ceph']

  # Nova
  $nova_services_list = [
    'nova-api',
    'nova-cert',
    'nova-consoleauth',
    'nova-conductor',
    'nova-scheduler',
    'nova-novncproxy',
  ]

  # Glance
  if $fuel_version >= '9.0' {
    $glance_services_list = ['glance-registry', 'glance-api', 'glance-glare']
  } else {
    $glance_services_list = ['glance-registry', 'glance-api']
  }

  # Neutron
  $neutron_services_list = [
    'neutron-server',
  ]

  # Cinder
  if $cinder_vol_on_ctrl {
    $cinder_services_list = [
      'cinder-api',
      'cinder-scheduler',
      'cinder-volume',
      'cinder-backup'
    ]
  } else {
    $cinder_services_list = [
      'cinder-api',
      'cinder-scheduler'
    ]
  }

  # Heat
  $heat_services_list = [
    'heat-api',
    'heat-api-cloudwatch',
    'heat-api-cfn',
  ]

  # Murano
  if $murano_enabled {
    $murano_services_list = ['murano-api', 'murano-engine']
  } else {
    $murano_services_list = []
  }

  # Sahara
  if $sahara_enabled {
    $sahara_services_list = ['sahara-all']
  } else {
    $sahara_services_list = []
  }

  # TODO(pchechetin): Add Ironic support

  # Pacemaker services
  $cluster_services_list = [
    'neutron-openvswitch-agent',
    'neutron-l3-agent',
    'neutron-metadata-agent',
    'neutron-dhcp-agent',
    'p_heat-engine',
  ]

  # Concatenate init services
  $init_services_list = concat(
    $nova_services_list,
    $glance_services_list,
    $neutron_services_list,
    $cinder_services_list,
    $heat_services_list,
    $murano_services_list,
    $sahara_services_list
  )

  # NOTE: Swift is not supported by Octane

}
