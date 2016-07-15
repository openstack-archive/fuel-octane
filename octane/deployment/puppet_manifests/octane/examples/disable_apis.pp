#enable admin level stats socket for haproxy
#disable certain openstack api services
#disable all corosync services except for
#
#"('p_mysql', 'p_haproxy', 'p_dns', 'p_ntp', 'vip',
#                             'p_conntrackd', 'p_rabbitmq-server',
#                             'clone_p_vrouter')"
$haproxy_resources_to_disable = get_apis_to_disable()
ensure_resource('haproxy_backend_server', $haproxy_resources_to_disable)