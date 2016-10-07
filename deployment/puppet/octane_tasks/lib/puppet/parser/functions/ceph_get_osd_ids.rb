Puppet::Parser::Functions.newfunction(:ceph_get_osd_ids, :arity => 1, :type => :rvalue) do |args|
  require 'json'
  hostname = args[0]

  ids = []
  output = JSON.parse(Puppet::Util::Execution.execute("ceph osd tree -f json"))
  output['nodes'].each do |n|
    if n['type'] == 'host' && n['name'] == hostname
      ids += n['children']
    end
  end
  ids
end
