
class octane_tasks::kill_cluster {
  exec { 'kill_cluster':
    command   => 'pcs cluster kill',
    provider  => shell,
  }
}
