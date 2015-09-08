# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import fuelclient
import json
import logging
import os.path
import time
import uuid
import yaml

from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane import magic_consts
from octane.util import ssh
from octane.util import subprocess

LOG = logging.getLogger(__name__)


def get_nodes(env, roles):
    for node in node_obj.Node.get_all():
        if node.data['cluster'] != env.data['id']:
            continue
        for role in roles:
            if (role in node.data['roles'] or
                    role in node.data['pending_roles']):
                yield node
                break


def get_controllers(env):
    controllers = get_nodes(env, ['controller'])
    return controllers


def get_one_controller(env):
    return next(get_controllers(env))


def change_env_settings(env_id, master_ip=''):
    # workaround for bugs related to DNS, NTP and TLS
    env = environment_obj.Environment(env_id)

    attrs = env.get_attributes()
    attrs['editable']['public_ssl']['horizon']['value'] = False
    attrs['editable']['public_ssl']['services']['value'] = False
    attrs['editable']['external_ntp']['ntp_list']['value'] = master_ip
    attrs['editable']['external_dns']['dns_list']['value'] = master_ip

    env.update_attributes(attrs)


def clone_env(env_id, release):
    LOG.info("Cloning env %s for release %s", env_id, release.data['name'])
    res = subprocess.call_output(
        ["fuel2", "env", "clone", "-f", "json",
         str(env_id), uuid.uuid4().hex, str(release.data['id'])],
    )
    for kv in json.loads(res):
        if kv['Field'] == 'id':
            seed_id = kv['Value']
            break
    else:
        raise Exception("Couldn't find new environment ID in fuel CLI output:"
                        "\n%s" % res)
    return seed_id


def delete_fuel_resources(env):
    node = get_one_controller(env)
    sftp = ssh.sftp(node)
    sftp.put(
        os.path.join(magic_consts.CWD, "helpers/delete_fuel_resources.py"),
        "/tmp/delete_fuel_resources.py",
    )
    ssh.call(
        ["sh", "-c", ". /root/openrc; python /tmp/delete_fuel_resources.py"],
        node=node,
    )


def parse_tenant_get(output, field):
    for line in output.splitlines()[3:-1]:
        parts = line.split()
        if parts[1] == field:
            return parts[3]
    raise Exception(
        "Field {0} not found in output:\n{1}".format(field, output))


def get_service_tenant_id(env, node=None):
    env_id = env.data['id']
    fname = os.path.join(
        magic_consts.FUEL_CACHE,
        "env-{0}-service-tenant-id".format(env_id),
    )
    if os.path.exists(fname):
        with open(fname) as f:
            return f.readline()

    if node is None:
        node = get_one_controller(env)

    password = get_admin_password(env, node)
    tenant_out = ssh.call_output(
        [
            'sh', '-c',
            '. /root/openrc; keystone --os-password={0} tenant-get services'
            .format(password),
        ],
        node=node,
    )
    tenant_id = parse_tenant_get(tenant_out, 'id')
    dname = os.path.dirname(fname)
    if not os.path.exists(dname):
        os.makedirs(dname)
    with open(fname, 'w') as f:
        f.write(tenant_id)
    return tenant_id


def wait_for_node(node, status, timeout=60 * 60, check_freq=60):
    node_id = node.data['id']
    LOG.debug("Waiting for node %s to transition to status '%s'",
              node_id, status)
    started_at = time.time()  # TODO: use monotonic timer
    while True:
        data = node.get_fresh_data()
        if data['status'] == 'error':
            raise Exception("Node %s fell into error status" % (node_id,))
        if data['online'] and data['status'] == status:
            LOG.info("Node %s transitioned to status '%s'", node_id, status)
            return
        if time.time() - started_at >= timeout:
            raise Exception("Timeout waiting for node %s to transition to "
                            "status '%s'" % (node_id, status))
        time.sleep(check_freq)


def wait_for_nodes(nodes, status, timeout=60 * 60, check_freq=60):
    for node in nodes:  # TODO: do this smarter way
        wait_for_node(node, status, timeout, check_freq)


def move_nodes(env, nodes):
    env_id = env.data['id']
    for node in nodes:
        node_id = node.data['id']
        subprocess.call(
            ["fuel2", "env", "move", "node", str(node_id), str(env_id)])
    wait_for_nodes(nodes, "provisioned")


def provision_nodes(env, nodes):
    env.install_selected_nodes('provision', nodes)
    wait_for_nodes(nodes, "provisioned")


def deploy_nodes(env, nodes):
    env.install_selected_nodes('deploy', nodes)
    wait_for_nodes(nodes, "ready")


def deploy_changes(env, nodes):
    env.deploy_changes()
    wait_for_nodes(nodes, "ready", timeout=180 * 60)


def merge_deployment_info(env):
    default_info = env.get_default_facts('deployment')
    try:
        deployment_info = env.get_facts('deployment')
    except fuelclient.cli.error.ServerDataException:
        LOG.warn('Deployment info is unchanged for env: %s',
                 env.id)
        deployment_info = []
    for info in default_info:
        if not (info['uid'], info['role']) in [(i['uid'], i['role'])
           for i in deployment_info]:
            deployment_info.append(info)
    return deployment_info


def get_astute_yaml(env, node=None):
    if not node:
        node = get_one_controller(env)
    with ssh.sftp(node).open('/etc/astute.yaml') as f:
        data = f.read()
    return yaml.load(data)


def get_admin_password(env, node=None):
    return get_astute_yaml(env, node)['access']['password']


def set_network_template(env, filename):
    with open(filename, 'r') as f:
        data = f.read()
        env.set_network_template_data(yaml.load(data))
