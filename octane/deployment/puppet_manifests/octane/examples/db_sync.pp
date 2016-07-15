$upgrade_hash = hiera_hash('upgrade')
$old_cluster_version = $upgrade_hash['general']['orig']['version']
$new_cluster_version = $upgrade_hash['general']['seed']['version']
if $old_cluster_version < 7.0 and $new_cluster_version >= 7.0
{
  class {'octane::flavors_migrate': venv => "/opt/virtualenvs/openstack-kilo/"}
}


$kilo_packages_venv_path = "/opt/virtualenvs/openstack-kilo/"
class {"::keystone::db::sync":}
class {"::glance::db::sync":}
class {"::heat::db::sync":}
class {"::nova::db::sync":}
class {"::neutron::db::sync":}

Exec <| tag == 'flavors_migrate_before' |> -> Class <| title == '::nova::db::sync' |>
Class <| title == '::nova::db::sync' |> -> Exec <| tag == 'flavors_migrate_after' |>