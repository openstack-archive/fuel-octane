Puppet::Parser::Functions.newfunction(:ceph_get_mon_ids, :type => :rvalue) do |args|
  require 'json'

  ids = []
  output = JSON.parse(Puppet::Util::Execution.execute("ceph status -f json"))
  ids += output['quorum']
  ids
end
