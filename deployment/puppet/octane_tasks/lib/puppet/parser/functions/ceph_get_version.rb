Puppet::Parser::Functions.newfunction(:ceph_get_version, :type => :rvalue) do |args|
  require 'json'

  service_type = args[0]
  id = '*'
  versions = {}


  version_string = Puppet::Util::Execution.execute("ceph tell #{service_type}.#{id} version -f json")
  version_string.lines.each do |line|
    line = line.strip
    if line.length > 0
      entity, version = line.split(" ", 2)
      entity = entity.tr(":", "")
      versions[entity] = JSON.parse(version)['version']
    end
  end
  versions
end
