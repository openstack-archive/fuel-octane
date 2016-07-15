require 'active_support/core_ext/hash/reverse_merge'

Puppet::Type.newtype(:dump_mysqlbases) do

  newparam(:name, :namevar => true) do
  end

  newparam(:databases) do
    desc 'list of databases'
    #munge do |value|
    #  value.to_a
    #end
  end

  newparam(:output_dir) do
    desc 'output directory'
    defaultto '/var/lib/fuel/db_dumps'
  end

    # Default resources for swift ring builder
  def resources
    resources = []

    default_database = {
        'user' => 'root',
        'mysql_port'=>3307,
        'host'=>'localhost',
    }

    default_command = { 'provider' => 'shell', 'logoutput' => 'true' }
    self[:databases].each do |database_name, database|
      database.reverse_merge! default_database
      command = "ssh #{database['host']} 'mysqldump --add-drop-database --lock-all-tables --single-transaction -u #{database['user']}
               --password=#{database['password']}  -d #{database_name} |
                gzip -9' > #{self[:output_dir]}/#{database_name}.sql.gz"
      title = "dump_#{database_name}_sql"
      
      
      resources += [Puppet::Type.type("exec".to_sym).new({:command =>command, :title=>title}.reverse_merge(default_command))]
    end
    resources
  end

  def eval_generate
    resources
  end
end
