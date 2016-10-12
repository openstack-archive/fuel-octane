# == Class: octane_tasks::stop_compute_service
#
# This class stops compute services to prepare
# for inplace package updates.
#
class octane_tasks::stop_compute_services {
  service { 'nova-compute':
    ensure    => stopped,
  }

  service { 'neutron-plugin-openvswitch-agent':
    ensure    => stopped,
  }
}
