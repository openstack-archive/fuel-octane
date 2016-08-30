Puppet::Parser::Functions.newfunction(:ceph_get_fsid, :arity => 1, :type => :rvalue) do |args|
  require 'shellwords'

  ceph_conf = Shellwords.escape(args[0])

  Puppet::Util::Execution.execute("ceph-conf -c #{ceph_conf} --lookup fsid")
end
