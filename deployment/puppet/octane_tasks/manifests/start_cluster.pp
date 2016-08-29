
class octane_tasks::start_cluster {
  exec { 'start_cluster':
    command   => 'pcs cluster start',
    provider  => shell,
  }
}
