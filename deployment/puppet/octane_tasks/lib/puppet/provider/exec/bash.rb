Puppet::Type.type(:exec).provide :bash, :parent => :posix do
  include Puppet::Util::Execution

  confine :feature => :posix

  desc <<-EOT
    Acts like shell provider, but adds `set -o pipefail` in front of any command to achive
    more reliable error handling of commands with pipes.
  EOT

  def run(command, check = false)
    super(['/bin/bash', '-c', "set -o pipefail; #{command}"], check)
  end

  def validatecmd(command)
    true
  end
end

