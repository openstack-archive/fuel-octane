# TODO(pchechetin): Uncomment when rspec-puppet is necessary.
# require 'rspec-puppet/rake_task'

require 'puppet-syntax/tasks/puppet-syntax'
require 'puppet-lint/tasks/puppet-lint'

PuppetLint.configuration.ignore_paths = ["spec/**/*.pp", "vendor/**/*.pp"]
PuppetLint.configuration.fail_on_warnings = true
PuppetLint.configuration.send('disable_class_inherits_from_params_class')

