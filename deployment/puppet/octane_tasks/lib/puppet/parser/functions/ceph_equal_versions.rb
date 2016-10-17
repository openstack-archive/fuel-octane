Puppet::Parser::Functions.newfunction(:ceph_equal_versions, :type => :rvalue) do |args|
  require 'json'

  versions_1 = args[0]
  versions_2 = args[1]

  # Pre-check all versions for consistency. Each hash MUST contain same
  # versions for all elements.
  v1_equal = versions_1.values.all? {|val| val == versions_1.values[0]}
  v2_equal = versions_2.values.all? {|val| val == versions_2.values[0]}

  # Either array contains some values, that are not equal. This means, that something
  # went wrong and relevant component has only been partially upgraded. Fail with info message.
  fail "Partial upgrade detected, aborting. Current version layout: #{versions_1}, #{versions_2}" unless v1_equal and v2_equal

  # Intersection of 2 arrays with any amount of equal elements will yield an
  # array with only one element 
  ret = (versions_1.values & versions_2.values).length == 1

  ret
end
