# == Class: octane_tasks::neutron_migrations_for_fuel_8
#
# This class is for fixing an issue with floating IPs (the issue has been introduced in Fuel 8.0)
# The issue is in Fuel 8.0 timeframe external network type has been switched from local to flat
# which renders all already allocated floating IPs useless.
#
class octane_tasks::neutron_migrations_for_fuel_8 {
  file { '/tmp/neutron_migrations_for_fuel_8':
    source => 'puppet:///modules/octane_tasks/neutron_migrations_for_fuel_8',
  }

  exec { 'mysql neutron < /tmp/neutron_migrations_for_fuel_8':
    provider    => shell,
    require     => File['/tmp/neutron_migrations_for_fuel_8'],
    environment => 'HOME=/root',
  }
}
