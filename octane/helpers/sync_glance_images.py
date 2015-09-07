# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import logging

from fuelclient.objects import environment as environment_obj

from octane.util import env as env_util
from octane.util import ssh


LOG = logging.getLogger(__name__)


def get_endpoint_ip(ep_name, yaml_data):
    endpoint = yaml_data['network_scheme']['endpoints'].get(ep_name)
    if not endpoint:
        return None
    net_data = endpoint["IP"][0]
    if net_data:
        return net_data.split('/')[0]


def get_glance_password(yaml_data):
    return yaml_data['glance']['user_password']


def parse_swift_out(output, field):
    for line in output.splitlines()[1:-1]:
        parts = line.split(': ')
        if parts[0].strip() == field:
            return parts[1]
    raise Exception(
        "Field {0} not found in output:\n{1}".format(field, output))


def get_swift_objects(node, tenant, user, password, token, container):
    cmd = ". /root/openrc; swift --os-project-name {0} --os-username {1}"\
        " --os-password {2} --os-auth-token {3} list {4}".format(tenant,
                                                                 user,
                                                                 password,
                                                                 token,
                                                                 container)
    objects_list, _ = ssh.call(["sh", "-c", cmd],
                               stdout=ssh.PIPE,
                               node=node)
    return objects_list.split('\n')[:-1]


def get_object_property(node, tenant, user, password, token, container,
                        object_id, prop):
    cmd = ". /root/openrc; swift --os-project-name {0} --os-username {1}"\
        " --os-password {2} --os-auth-token {3} stat {4} {5}"\
        .format(tenant,
                user,
                password,
                token,
                container,
                object_id)
    object_data, _ = ssh.call(["sh", "-c", cmd],
                              stdout=ssh.PIPE,
                              node=node)
    return parse_swift_out(object_data, prop)


def get_auth_token(node, tenant, user, password):
    cmd = ". /root/openrc; keystone --os-tenant-name {0}"\
        " --os-username {1} --os-password {2} token-get".format(tenant,
                                                                user,
                                                                password)
    token_info, _ = ssh.call(["sh", "-c", cmd],
                             stdout=ssh.PIPE,
                             node=node)
    return env_util.parse_tenant_get(token_info, 'id')


def download_image(node, tenant, user, password, token, container, object_id):
    cmd = ". /root/openrc; swift --os-project-name {0} --os-username {1}"\
        " --os-password {2} --os-auth-token {3} download {4} {5}"\
        .format(tenant,
                user,
                password,
                token,
                container,
                object_id)
    ssh.call(["sh", "-c", cmd], node=node)
    LOG.info("Swift %s image has been downloaded" % object_id)


def delete_image(node, tenant, user, password, token, container, object_id):
    cmd = ". /root/openrc; swift --os-project-name {0}"\
        " --os-username {1} --os-password {2} --os-auth-token {3}"\
        " delete {4} {5}".format(tenant, user, password, token,
                                 container, object_id)
    ssh.call(["sh", "-c", cmd], node=node)
    LOG.info("Swift %s image has been deleted" % object_id)


def transfer_image(node, tenant, user, password, token, container, object_id,
                   storage_ip, tenant_id):
    storage_url = "http://{0}:8080/v1/AUTH_{1}".format(storage_ip, tenant_id)
    cmd = ['swift', '--os-project-name', tenant, '--os-username', user,
           '--os-password', password, '--os-auth-token', token,
           '--os-storage-url', storage_url, 'upload', container,
           object_id]
    ssh.call(cmd, node=node)
    LOG.info("Swift %s image has been transferred" % object_id)


def sync_glance_images(source_env_id, seed_env_id, seed_swift_ep):
    """Sync glance images from original ENV to seed ENV

    Args:
        source_env_id (int): ID of original ENV.
        seed_env_id (int): ID of seed ENV.
        seed_swift_ep (str): endpoint's name where swift-proxy service is
                             listening on.

    Examples:
        sync_glance_images(2, 3, 'br-mgmt')
    """
    # set glance username
    glance_user = "glance"
    # set swift container value
    container = "glance"
    # choose tenant
    tenant = "services"
    # get clusters by id
    source_env = environment_obj.Environment(source_env_id)
    seed_env = environment_obj.Environment(seed_env_id)
    # gather cics admin IPs
    source_node = next(env_util.get_controllers(source_env))
    seed_node = next(env_util.get_controllers(seed_env))
    # get cics yaml files
    source_yaml = env_util.get_astute_yaml(source_env, source_node)
    seed_yaml = env_util.get_astute_yaml(seed_env, seed_node)
    # get glance passwords
    source_glance_pass = get_glance_password(source_yaml)
    seed_glance_pass = get_glance_password(seed_yaml)
    # get seed node swift ip
    seed_swift_ip = get_endpoint_ip(seed_swift_ep, seed_yaml)
    # get service tenant id & lists of objects for source env
    source_token = get_auth_token(source_node, tenant, glance_user,
                                  source_glance_pass)
    source_swift_list = set(get_swift_objects(source_node,
                                              tenant,
                                              glance_user,
                                              source_glance_pass,
                                              source_token,
                                              container))
    # get service tenant id & lists of objects for seed env
    seed_token = get_auth_token(seed_node, tenant, glance_user,
                                seed_glance_pass)
    seed_swift_list = set(get_swift_objects(seed_node,
                                            tenant,
                                            glance_user,
                                            seed_glance_pass,
                                            seed_token,
                                            container))
    # get service tenant for seed env
    seed_tenant = env_util.get_service_tenant_id(seed_env)
    # check consistency of matched images
    source_token = get_auth_token(source_node, tenant, glance_user,
                                  source_glance_pass)
    seed_token = get_auth_token(seed_node, tenant, glance_user,
                                seed_glance_pass)
    for image in source_swift_list & seed_swift_list:
        source_obj_etag = get_object_property(source_node,
                                              tenant,
                                              glance_user,
                                              source_glance_pass,
                                              source_token,
                                              container,
                                              image,
                                              'ETag')
        seed_obj_etag = get_object_property(seed_node, tenant,
                                            glance_user, seed_glance_pass,
                                            seed_token, container, image,
                                            'ETag')
        if source_obj_etag != seed_obj_etag:
            # image should be resynced
            delete_image(seed_node, tenant, glance_user, seed_glance_pass,
                         seed_token, container, image)
            LOG.info("Swift %s image should be resynced" % image)
            seed_swift_list.remove(image)
    # migrate new images
    for image in source_swift_list - seed_swift_list:
        # download image on source's node local drive
        source_token = get_auth_token(source_node, tenant, glance_user,
                                      source_glance_pass)
        download_image(source_node, tenant, glance_user, source_glance_pass,
                       source_token, container, image)
        # transfer image
        source_token = get_auth_token(source_node, tenant,
                                      glance_user, source_glance_pass)
        seed_token = get_auth_token(seed_node, tenant, glance_user,
                                    seed_glance_pass)
        transfer_image(source_node, tenant, glance_user, seed_glance_pass,
                       seed_token, container, image, seed_swift_ip,
                       seed_tenant)
        # remove transferred image
        ssh.sftp(source_node).remove(image)
    # delete outdated images
    for image in seed_swift_list - source_swift_list:
        token = get_auth_token(seed_node, tenant, glance_user,
                               seed_glance_pass)
        delete_image(seed_node, tenant, glance_user, seed_glance_pass,
                     token, container, image)
