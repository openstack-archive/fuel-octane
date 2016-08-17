# == Class: octane_tasks::migrate_flavor_data_70
#
# This class is for migrating nova db entries to new format
#
class octane_tasks::migrate_flavor_data_70 (
) inherits octane_tasks::params {

  if $fuel_version == '7.0' {
    exec { 'nova-manage db migrate_flavor_data':
      path => ['/usr/bin', '/usr/sbin'],
    }
  }
}
