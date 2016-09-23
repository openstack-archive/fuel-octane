# == Class: octane_tasks::preupgrade_compute
#
# This class upgrades following packages on compute node
# inplace: 
#
class octane_tasks::preupgrade_compute {
  $preupgrade_packages = hiera('preupgrade_packages')
  $preupgrade_packages_str = join(regsubst($preupgrade_packages, '.*', '\\0=\\*'), ' ')

  # As much as I would love to use package type, it just won't
  # cut it. The to-be-updated packages have dependencies between
  # each other, so it would take a strict ordering of the package
  # list to do so. Assuming that passing the list to the resource
  # makes Puppet realize these resources in the same order, they
  # are present in the list.
  exec { 'upgrade-packages':
    path        => '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
    command     => "apt-get install --only-upgrade --yes --force-yes \
                    -o Dpkg::Options::=\"--force-confdef\" \
                    -o Dpkg::Options::=\"--force-confold\" \
                    ${preupgrade_packages_str}",
    environment => ['DEBIAN_FRONTEND=noninteractive'],
    before      => Anchor['packages-are-updated'],
  }
  #package { $preupgrade_packages:
  #  ensure          => latest,
  #  install_options => "--only-upgrade",
  #  provider        => 'apt_future',
  #  before          => Anchor['packages-are-updated'],
  #}

  anchor { 'packages-are-updated': }

  service { 'nova-compute':
    ensure    => running,
    subscribe => Anchor['packages-are-updated'],
  }

  service { 'neutron-plugin-openvswitch-agent':
    ensure    => running,
    subscribe => Anchor['packages-are-updated'],
  }
}
