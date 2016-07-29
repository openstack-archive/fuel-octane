class { 'octane_tasks::maintenance':
  ensure_cluster_services => 'stopped',
  ensure_init_services    => 'stopped',
}
