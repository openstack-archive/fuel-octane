# == Class: octane_tasks::dbsync
#
# This class is for applying latest database migrations
#
class octane_tasks::dbsync (
) inherits octane_tasks::params {

  include ::keystone::db::sync
  include ::nova::db::sync
  include ::glance::db::sync
  include ::neutron::db::sync
  include ::cinder::db::sync
  include ::heat::db::sync

  if $octane_tasks::params::murano_enabled or $octane_tasks::params::murano_plugin_enabled {
    include ::murano::db::sync
  }

  if $octane_tasks::params::sahara_enabled {
    include ::sahara::db::sync
  }

  if $octane_tasks::params::ironic_enabled {
    include ::ironic::db::sync
  }

  # All db sync classes have "refreshonly => true" by default
  Exec <||> {
    refreshonly => false
  }
}
