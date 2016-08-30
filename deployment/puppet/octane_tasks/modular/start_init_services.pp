notice('MODULAR: octane_tasks::start_init_services')

class {'octane_tasks::maintenance':
  ensure_init_services => 'running',
}
