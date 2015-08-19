from octane.commands.upgrade_db import get_controllers
from fuelclient.objects import environment as environment_obj
from octane.util import ssh


def get_astute_yaml(node):
    data, _ = ssh.call(['cat', '/etc/astute.yaml'], stdout=ssh.PIPE, node=node)
    return yaml.load(data)


def get_endpoint_ip(ep_name, yaml_data):
    if ep_name not in yaml_data['network_scheme']['endpoints']:
        return None
    return yaml_data['network_scheme']['endpoints'][ep_name]["IP"][0]


def get_glance_password(yaml_data):
    return yaml_data['glance']['user_password']


def get_service_tenant_id(node):
    tenant_id, _ = ssh.call(["bash", "-c", ". /root/openrc;",
                             "keystone tenant-list | ",
                             "awk '/services/{print $2}'"],
                            stdout=ssh.PIPE,
                            node=node)
    return tenant_id


def get_swift_objects(node, token, container):
    objects_list, _ = ssh.call(["bash", "-c", ". /root/openrc;",
                                "swift --os-auth-token %s" % token,
                                "list", container],
                               stdout=ssh.PIPE,
                               node=node)
    return objects_list


# TODO
def get_auth_token(node, tenant, username, password):
    token, _ = ssh.call(["bash", "-c", ". /root/openrc;",
                         "keystone tenant-list | ",
                         "  awk -F\| '\$2 ~ /id/{print \$3}' | tr -d \ "],
                        stdout=ssh.PIPE,
                        node=node)
    return tenant_id
    # . openrc;
    # keystone --os-username=${username} --os-password=${password} \
    # --os-tenant-name=${tenant} token-get \
    # | grep ' id ' | cut -d \| -f 3 | tr -d


def download_glance_image(node, token, object_id):
    ssh.call(["bash", "-c", ". /root/openrc;",
              "swift --os-auth-token", token,
              "download glance %s" % object_id],
             stdout=ssh.PIPE,
             node=source_node)


def delete_glance_image(node, token, object_id):
    ssh.call(["bash", "-c", ". /root/openrc;",
              "swift --os-auth-token", token,
              "delete glance %s" % object_id],
             stdout=ssh.PIPE,
             node=source_node)


def transfer_glance_image(source_node, storage_ip, tenant_id,
                          dest_token, object_id):
    ssh.call(["swift --os-auth-token", dest_token,
              "--os-storage-url",
              "http://{0}:8080/v1/AUTH_{1}".format(storage_ip, tenant_id),
              "upload glance %s" % object_id],
             stdout=ssh.PIPE,
             node=source_node)


def sync_glance_images(source_env_id, seed_env_id):
    # set swift container value
    container = "glance"
    # choose tenant
    tenant = "services"
    # should be specified by user or parsed from template?
    swift_ep = "bond-swift"
    username = glance
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
    source_swift_list = set(get_swift_objects(source_node, source_token,
                                              container))
    # get service tenant id & lists of objects for seed env
    seed_token = get_auth_token(seed_node, tenant, username, seed_glance_pass)
    seed_swift_list = set(get_swift_objects(seed_node, seed_token, container))
    # get service tenant for seed env
    seed_token = get_service_tenant_id(seed_node)
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
