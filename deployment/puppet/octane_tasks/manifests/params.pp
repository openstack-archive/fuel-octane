# == Class: octane_tasks::params
#
# This class contains paramaters for octane_tasks
#
class octane_tasks::params (
) {

  $ceilometer_hash  = hiera_hash('ceilometer', {'enabled' => false})
  $sahara_hash      = hiera_hash('sahara', {'enabled' => false})
  $murano_hash      = hiera_hash('murano', {'enabled' => false})

  $ceilometer_enabled  = $ceilometer_hash['enabled']
  $sahara_enabled      = $sahara_hash['enabled']
  $murano_enabled      = $murano_hash['enabled']

  $nova_services_list = [
    'nova-api',
    'nova-cert',
    'nova-consoleauth',
    'nova-conductor',
    'nova-scheduler',
    'nova-novncproxy',
  ]

  # TODO: Add glance-glare for 9.0
  $glance_services_list = [
    'glance-registry',
    'glance-api',
  ]

  $neutron_services_list = [
    'neutron-server',
  ]

  # TODO: Add cinder-volume if ceph used
  $cinder_services_list = [
    'cinder-api',
    'cinder-scheduler',
  ]

  $heat_services_list = [
    'heat-api',
    'heat-api-cloudwatch',
    'heat-api-cfn',
  ]

  $cluster_services_list = [
    'neutron-openvswitch-agent',
    'neutron-l3-agent',
    'neutron-metadata-agent',
    'neutron-dhcp-agent',
    'p_heat-engine',
  ]

  $init_services_list = concat(
    $nova_services_list,
    $glance_services_list,
    $neutron_services_list,
    $cinder_services_list,
    $heat_services_list
  )

  # TODO: Murano, Sahara, Ceilometer
  # NOTE: Swift is not supported by Octane

}
