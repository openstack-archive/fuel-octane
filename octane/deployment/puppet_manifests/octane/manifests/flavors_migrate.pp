class octane::flavors_migrate ($venv)
{
  $pre_commands = [
    "nova-manage db sync --version 290",
    "nova-manage db migrate_flavor_data"
  ]

  $post_commands = [
    "nova-manage db expand",
    "nova-manage db migrate"
  ]

  octane::common::venv_exec { $pre_commands: venv => $venv, tag => ['kilo_venv', 'flavors_migrate_before']}
  octane::common::venv_exec { $post_commands: venv => $venv, tag => ['kilo_venv', 'flavors_migrate_after']}

  package {"nova-kilo-openstack-venv": }

}