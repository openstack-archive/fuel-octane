Puppet::Parser::Functions.newfunction(:ceph_get_fsid, :arity => 1, :type => :rvalue) do |args|
  # NOTE(pchechetin): In case everyting else doesn't work, use approch below.
  #                   But it's required to install augeas-tools package (Ubuntu) before execution.
  #
  # Puppet::Util::Execution.execute("echo 'get /files/etc/ceph/ceph.conf/global/fsid' | augtool -t 'Rsyncd incl /etc/ceph/ceph.conf' | cut -d' ' -f3")
  require 'augeas'

  ceph_conf = args[0]

  Augeas::open(nil, nil, Augeas::NO_MODL_AUTOLOAD) do |aug|
    aug.transform(:lens => "Rsyncd.lns", :incl => ceph_conf)
    aug.load
    aug.get("/files#{ceph_conf}/global/fsid")
  end
end
