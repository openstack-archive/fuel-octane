class { 'octane_tasks::maintenance':
  ensure_cluster_services => 'running',
  ensure_init_services    => 'running',
}
