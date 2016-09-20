# == Class: octane_tasks::neutron_migrations_for_fuel_8
#
# This class is for fixing an issue with floating IPs
# (the issue was introduced in Fuel 8.0)
#
class octane_tasks::neutron_migrations_for_fuel_8 {
  file { '/tmp/neutron_migrations_for_fuel_8':
    source => 'puppet:///modules/octane_tasks/neutron_migrations_for_fuel_8',
  }

  exec { 'mysql neutron < /tmp/neutron_migrations_for_fuel_8':
    provider    => shell,
    require     => File['/tmp/neutron_migrations_for_fuel_8'],
    environment => "HOME=/root",
  }
}
