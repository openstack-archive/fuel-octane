# == Class: octane_tasks::start_cluster
#
# Starts Pacemaker cluster again (on rollback phase).
#
class octane_tasks::start_cluster {
  exec { 'start_cluster':
    command  => 'pcs cluster start',
    provider => shell,
  }
}
