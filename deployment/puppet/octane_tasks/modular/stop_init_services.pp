notice('MODULAR: octane_tasks::stop_init_services')

class { 'octane_tasks::maintenance':
  ensure_init_services => 'stopped',
}
