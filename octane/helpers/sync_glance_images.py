import yaml
from octane.commands.upgrade_db import get_controllers
from fuelclient.objects import environment as environment_obj
from octane.util import ssh


def get_astute_yaml(node):
    data = None
    with ssh.sftp(node).open('/etc/astute.yaml') as f:
        data = f.read()
    return yaml.load(data)


def get_endpoint_ip(ep_name, yaml_data):
    if ep_name not in yaml_data['network_scheme']['endpoints']:
        return None
    return yaml_data['network_scheme']['endpoints'][ep_name]["IP"][0]


def get_glance_password(yaml_data):
    return yaml_data['glance']['user_password']


def parse_keystone_get(output, field):
    for line in output.splitlines()[3:-1]:
        parts = line.split()
        if parts[1] == field:
            return parts[3]
    raise Exception(
        "Field {0} not found in output:\n{1}".format(field, output))


def get_tenant_id(node, tenant):
    ssh_line = ". /root/openrc; keystone tenant-get {0}".format(tenant)
    tenant_info, _ = ssh.call(["sh", "-c", ssh_line],
                              stdout=ssh.PIPE,
                              node=node)
    return parse_keystone_get(tenant_info, 'id')


def get_swift_objects(node, username, password, token, container, tenant):
    ssh_line = ". /root/openrc; swift --os-username {0} --os-password {1}"\
        " --os-auth-token {2} --os-project-name {3} list {4}".format(username,
                                                                     password,
                                                                     token,
                                                                     tenant,
                                                                     container)
    objects_list, _ = ssh.call(["sh", "-c", ssh_line],
                               stdout=ssh.PIPE,
                               node=node)
    return objects_list.split('\n')[:-1]


def get_auth_token(node, tenant, username, password):
    ssh_line = ". /root/openrc; keystone --os-username={0} --os-password={1}"\
        " --os-tenant-name={2} token-get".format(username, password, tenant)
    token_info, _ = ssh.call(["sh", "-c", ssh_line],
                             stdout=ssh.PIPE,
                             node=node)
    return parse_keystone_get(token_info, 'id')


def download_glance_image(node, container, token, object_id):
    ssh_line = ". /root/openrc; swift --os-auth-token {0} download {1} {2}"\
        .format(token, container, object_id)
    ssh.call(["sh", "-c", ssh_line], stdout=ssh.PIPE, node=node)


def delete_glance_image(node, container, token, object_id):
    ssh_line = ". /root/openrc; swift --os-auth-token {0} delete {1} {2}"\
        .format(token, container, object_id)
    ssh.call(["sh", "-c", ssh_line], stdout=ssh.PIPE, node=node)


def transfer_glance_image(source_node, storage_ip, tenant_id,
                          dest_token, object_id):
    ssh_line = ". /root/openrc; swift --os-auth-token {0} --os-storage-url " +\
        "http://{1}:8080/v1/AUTH_{2} upload glance {3}".format(dest_token,
                                                               storage_ip,
                                                               tenant_id,
                                                               object_id)
    ssh.call(["sh", "-c", ssh_line], stdout=ssh.PIPE, node=source_node)


def sync_glance_images(source_env_id, seed_env_id):
    # set swift container value
    container = "glance"
    # choose tenant
    tenant = "services"
    # should be specified by user or parsed from template?
    swift_ep = "bond-swift"
    username = "glance"
    # get clusters by id
    source_env = environment_obj.Environment(source_env_id)
    seed_env = environment_obj.Environment(seed_env_id)
    # gather cics admin IPs
    source_node = get_controllers(source_env).next()
    seed_node = get_controllers(seed_env).next()
    # get cics yaml files
    source_yaml = get_astute_yaml(source_node)
    seed_yaml = get_astute_yaml(seed_node)
    # get glance passwords
    source_glance_pass = get_glance_password(source_yaml)
    seed_glance_pass = get_glance_password(seed_yaml)
    # get seed node swift ip
    seed_swift_ip = get_endpoint_ip(swift_ep, seed_yaml)
    # get service tenant id & lists of objects for source env
    source_token = get_auth_token(source_node, tenant, username,
                                  source_glance_pass)
    source_node, username, source_glance_pass, source_token, container, tenant
    source_swift_list = set(get_swift_objects(source_node, username,
                                              source_glance_pass, source_token,
                                              container, tenant))
    # get service tenant id & lists of objects for seed env
    seed_token = get_auth_token(seed_node, tenant, username, seed_glance_pass)
    seed_swift_list = set(get_swift_objects(source_node, username,
                                            seed_glance_pass, seed_token,
                                            container, tenant))
    # get service tenant for seed env
    seed_token = get_tenant_id(seed_node, tenant)
    # migrate new images
    for image in source_swift_list - seed_swift_list:
        # download image on source's node local drive
        source_token = get_auth_token(source_node, tenant, username,
                                      source_glance_pass)
        download_glance_image(source_node, source_token, image)
        # transfer image
        source_token = get_auth_token(source_node, tenant, username,
                                      source_glance_pass)
        seed_token = get_auth_token(seed_node, tenant, username,
                                    seed_glance_pass)
        transfer_glance_image(source_node, seed_swift_ip,
                              dest_token, image)
        # remove transferred image
        delete_file(node, object_id)
    # delete outdated images
    for image in seed_swift_list - source_swift_list:
        token = get_auth_token(seed_node, tenant, username, seed_glance_pass)
        delete_glance_image(seed_node, token, image)
