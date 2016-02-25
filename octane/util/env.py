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
from fuelclient.objects import task as task_obj

from octane.helpers import tasks as tasks_helpers
from octane.helpers import transformations
from octane import magic_consts
from octane.util import ssh
from octane.util import subprocess
from octane.util import plugin

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


def get_env_networks(env):
    network_data = env.get_network_data()
    return network_data['networks']


def get_env_provision_method(env):
    attrs = env.get_attributes()
    if 'provision' in attrs['editable']:
        return attrs['editable']['provision']['method']['value']
    else:
        return 'cobbler'


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


def clone_ips(orig_id, networks):
    call_args = ['fuel2', 'env', 'clone-ips', str(orig_id)]
    if networks:
        call_args += ['--networks'] + networks
    subprocess.call(call_args)


def delete_fuel_resources(env):
    node = get_one_controller(env)
    sftp = ssh.sftp(node)
    sftp.put(
        os.path.join(magic_consts.CWD, "helpers/delete_fuel_resources.py"),
        "/tmp/delete_fuel_resources.py",
    )
    command = ". /root/openrc; python /tmp/delete_fuel_resources.py"
    if plugin.is_contrail_plugin_enabled(env):
        command += " --skip-neutron"
    ssh.call(
        ["sh", "-c", command],
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
    return tenant_id


def cache_service_tenant_id(env, node=None):
    env_id = env.data['id']
    fname = os.path.join(
        magic_consts.FUEL_CACHE,
        "env-{0}-service-tenant-id".format(env_id),
    )
    if os.path.exists(fname):
        with open(fname) as f:
            return f.readline()

    tenant_id = get_service_tenant_id(env, node)
    dname = os.path.dirname(fname)
    if not os.path.exists(dname):
        os.makedirs(dname)
    with open(fname, 'w') as f:
        f.write(tenant_id)
    return tenant_id


def wait_for_env(cluster, status, timeout=60 * 60, check_freq=60):
    cluster_id = cluster.data['id']
    LOG.debug("Waiting for cluster %s to transition to status '%s'",
              cluster_id, status)
    started_at = time.time()  # TODO: use monotonic timer
    while True:
        real_status = cluster.status
        if real_status == 'error':
            raise Exception("Cluster %s fell into error status" %
                            (cluster_id,))
        if real_status == status:
            LOG.info("Cluster %s transitioned to status '%s'", cluster_id,
                     status)
            return
        if time.time() - started_at >= timeout:
            raise Exception("Timeout waiting for cluster %s to transition to "
                            "status '%s'" % (cluster_id, status))
        time.sleep(check_freq)


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


def wait_for_tasks(env, status, timeout=60 * 60, check_freq=60):
    env_id = env.data['id']
    LOG.debug("Waiting for env %s to have no '%s' tasks",
              env_id, status)
    started_at = time.time()  # TODO: use monotonic timer
    while True:
        tasks = task_obj.Task.get_all_data()
        cl_tasks = []
        for task in tasks:
            if task['cluster'] == env_id and task['status'] == status:
                cl_tasks.append(task)
        if not cl_tasks:
            LOG.info("Env %s have no '%s' tasks", env_id, status)
            return
        if time.time() - started_at >= timeout:
            raise Exception("Timeout waiting for env %s to complete "
                            "all tasks status" % env_id)
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
    LOG.info("Nodes provision started. Please wait...")
    wait_for_nodes(nodes, "provisioned")


def provision_nodes(env, nodes):
    env.install_selected_nodes('provision', nodes)
    LOG.info("Nodes provision started. Please wait...")
    wait_for_nodes(nodes, "provisioned", timeout=180 * 60)


def deploy_nodes(env, nodes):
    env.install_selected_nodes('deploy', nodes)
    LOG.info("Nodes deploy started. Please wait...")
    wait_for_nodes(nodes, "ready", timeout=180 * 60)
    wait_for_tasks(env, "running")


def deploy_changes(env, nodes):
    env.deploy_changes()
    LOG.info("Nodes deploy started. Please wait...")
    wait_for_env(env, "operational", timeout=180 * 60)


def get_deployment_info(env):
    deployment_info = []
    try:
        deployment_info = env.get_facts('deployment')
    except fuelclient.cli.error.ServerDataException:
        LOG.warn('Deployment info is unchanged for env: %s',
                 env.id)
    deployment_info = [x for x in deployment_info
                       if x['role'] != 'primary-controller']
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


def update_deployment_info(env, isolated):
    default_info = env.get_default_facts('deployment')
    network_data = env.get_network_data()
    gw_admin = transformations.get_network_gw(network_data,
                                              "fuelweb_admin")
    if isolated:
        # From backup_deployment_info
        backup_path = os.path.join(
            magic_consts.FUEL_CACHE,
            "deployment_{0}.orig".format(env.id),
        )
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        # Roughly taken from Environment.write_facts_to_dir
        for info in default_info:
            fname = os.path.join(
                backup_path,
                "{0}_{1}.yaml".format(info['role'], info['uid']),
            )
            with open(fname, 'w') as f:
                yaml.safe_dump(info, f, default_flow_style=False)
    deployment_info = []
    for info in default_info:
        if isolated:
            transformations.remove_ports(info)
            transformations.reset_gw_admin(info, gw_admin)
        # From run_ping_checker
        info['run_ping_checker'] = False
        transformations.remove_predefined_nets(info)
        deployment_info.append(info)
    env.upload_facts('deployment', deployment_info)

    tasks = env.get_deployment_tasks()
    tasks_helpers.skip_tasks(tasks)
    env.update_deployment_tasks(tasks)


def find_node_deployment_info(node, roles, data):
    node_roles = [n['role']
                  for n in data[0]['nodes'] if str(node.id) == n['uid']]
    if not set(roles) & set(node_roles):
        return None

    for info in data:
        if info['uid'] == str(node.id):
            return info
    return None


def get_backup_deployment_info(env_id):
    deployment_info = []
    backup_path = os.path.join(
        magic_consts.FUEL_CACHE, 'deployment_{0}.orig'.format(env_id))
    if not os.path.exists(backup_path):
        return None

    for filename in os.listdir(backup_path):
        filepath = os.path.join(backup_path, filename)
        with open(filepath) as info_file:
            info = yaml.safe_load(info_file)
            deployment_info.append(info)

    return deployment_info


def collect_deployment_info(env, nodes):
    deployment_info = []
    for node in nodes:
        info = get_astute_yaml(env, node)
        deployment_info.append(info)
    return deployment_info


def iter_deployment_info(env, roles):
    controllers = list(get_controllers(env))
    full_info = get_backup_deployment_info(env.id)
    roles = ['primary-controller', 'controller']

    if not full_info:
        full_info = collect_deployment_info(env, controllers)

    for node in controllers:
        info = find_node_deployment_info(node, roles, full_info)
        yield (node, info)
