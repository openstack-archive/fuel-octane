require 'rspec-puppet/rake_task'

begin
  if Gem::Specification::find_by_name('puppet-lint')
    require 'puppet-lint/tasks/puppet-lint'
    PuppetLint.configuration.ignore_paths = ["spec/**/*.pp", "vendor/**/*.pp"]
    PuppetLint.configuration.send('disable_class_inherits_from_params_class')
    PuppetLint.configuration.send('disable_variable_scope')
    task :default => [:rspec, :lint]
  end
rescue Gem::LoadError
  task :default => :rspec
end
