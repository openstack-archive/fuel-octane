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

import json
import logging
import os.path
import shutil
import time
import uuid
import yaml

from distutils import version

from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj
from fuelclient.objects import task as task_obj

from octane.helpers import tasks as tasks_helpers
from octane.helpers import transformations
from octane import magic_consts
from octane.util import disk
from octane.util import helpers
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


def get_one_node_of(env, role):
    return next(get_nodes(env, [role]))


def get_env_networks(env):
    network_data = env.get_network_data()
    return network_data['networks']


def get_env_provision_method(env):
    attrs = env.get_attributes()
    if 'provision' in attrs['editable']:
        return attrs['editable']['provision']['method']['value']
    else:
        return 'cobbler'


def clone_env(env_id, release):
    LOG.info("Cloning env %s for release %s", env_id, release.data['name'])
    res_json = fuel2_env_call(["clone", "-f", "json", str(env_id),
                               uuid.uuid4().hex, str(release.data['id'])],
                              output=True)
    res = json.loads(res_json)
    res = helpers.normalized_cliff_show_json(res)
    if 'id' in res:
        return res['id']

    raise Exception("Couldn't find new environment ID in fuel CLI output:"
                    "\n%s" % res)


def clone_ips(orig_id, networks):
    call_args = ['clone-ips', str(orig_id)]
    if networks:
        call_args += ['--networks'] + networks
    fuel2_env_call(call_args)


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


def move_nodes(env, nodes, provision=True, roles=None):
    env_id = env.data['id']
    cmd = ["move", "node"]
    if not provision:
        cmd += ['--no-provision']
    if roles:
        cmd += ['--roles', ','.join(roles)]
    for node in nodes:
        node_id = node.data['id']
        cmd_move_node = cmd + [str(node_id), str(env_id)]
        if provision and incompatible_provision_method(env):
            disk.create_configdrive_partition(node)
        fuel2_env_call(cmd_move_node)
    if provision:
        LOG.info("Nodes provision started. Please wait...")
        wait_for_nodes(nodes, "provisioned")


def copy_vips(env):
    fuel2_env_call(["copy", "vips", str(env.data['id'])])


def fuel2_env_call(args, output=False):
    cmd = ["fuel2", "--debug", "env"] + args
    if output:
        return subprocess.call_output(cmd)
    else:
        subprocess.call(cmd)


def provision_nodes(env, nodes):
    env.install_selected_nodes('provision', nodes)
    LOG.info("Nodes provision started. Please wait...")
    wait_for_nodes(nodes, "provisioned", timeout=180 * 60)


def deploy_nodes_without_tasks(env, nodes, skipped_tasks):
    tasks_to_execute = env.get_tasks(skip=skipped_tasks)
    env.execute_tasks(nodes, tasks_to_execute, False)
    LOG.info("Nodes deploy started. Please wait...")
    wait_for_nodes_tasks(env, nodes)


def wait_for_nodes_tasks(env, nodes):
    wait_for_nodes(nodes, "ready", timeout=180 * 60)
    wait_for_tasks(env, "running")


def deploy_nodes(env, nodes):
    env.install_selected_nodes('deploy', nodes)
    LOG.info("Nodes deploy started. Please wait...")
    wait_for_nodes(nodes, "ready", timeout=180 * 60)
    wait_for_tasks(env, "running")


def deploy_changes(env, nodes):
    env.deploy_changes()
    LOG.info("Nodes deploy started. Please wait...")
    wait_for_env(env, "operational", timeout=180 * 60)


def prepare_net_info(info):
    quantum_settings = info["quantum_settings"]
    pred_nets = quantum_settings["predefined_networks"]
    phys_nets = quantum_settings["L2"]["phys_nets"]
    if 'net04' in pred_nets and \
            pred_nets['net04']['L2']['network_type'] == "vlan":
        physnet = pred_nets["net04"]["L2"]["physnet"]
        segment_id = phys_nets[physnet]["vlan_range"].split(":")[1]
        pred_nets['net04']["L2"]["segment_id"] = segment_id


def get_astute_yaml(env, node=None):
    if not node:
        node = get_one_controller(env)
    with ssh.sftp(node).open('/etc/astute.yaml') as f:
        data = f.read()
    return yaml.load(data)


def get_admin_password(env, node=None):
    return get_astute_yaml(env, node)['access']['password']


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
        prepare_net_info(info)
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
    backup_path = get_dir_deployment_info(env_id)
    if not os.path.exists(backup_path):
        return None

    for filename in os.listdir(backup_path):
        filepath = os.path.join(backup_path, filename)
        with open(filepath) as info_file:
            info = yaml.safe_load(info_file)
            deployment_info.append(info)

    return deployment_info


def get_dir_deployment_info(env_id):
    backup_path = os.path.join(
        magic_consts.FUEL_CACHE,
        "deployment_{0}.orig".format(env_id),
    )
    return backup_path


def write_facts_to_dir(facts, env_id):
    backup_path = get_dir_deployment_info(env_id)
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    for info in facts:
        fname = os.path.join(
            backup_path,
            "{0}.yaml".format(info['uid']),
        )
        with open(fname, 'w') as f:
            yaml.safe_dump(info, f, default_flow_style=False)


def collect_deployment_info(env, nodes):
    deployment_info = []
    for node in nodes:
        info = get_astute_yaml(env, node)
        deployment_info.append(info)
    return deployment_info


def iter_deployment_info(env, roles):
    controllers = list(get_controllers(env))
    full_info = get_backup_deployment_info(env.id)

    if not full_info:
        full_info = collect_deployment_info(env, controllers)

    for node in controllers:
        info = find_node_deployment_info(node, roles, full_info)
        yield (node, info)


def incompatible_provision_method(env):
    if env.data.get("fuel_version"):
        env_version = version.StrictVersion(env.data["fuel_version"])
    else:
        error_message = ("Cannot find version of environment {0}:"
                         " attribute 'fuel_version' missing or has"
                         " incorrect value".format(env.data["id"]))
        raise Exception(error_message)
    provision_method = get_env_provision_method(env)
    if env_version < version.StrictVersion(magic_consts.COBBLER_DROP_VERSION) \
            and provision_method != 'image':
        return True
    return False


def copy_fuel_keys(source_env_id, seed_env_id):
    source_env_keys_path = os.path.join(
        magic_consts.FUEL_KEYS_BASE_PATH,
        str(source_env_id)
    )
    seed_env_keys_path = os.path.join(
        magic_consts.FUEL_KEYS_BASE_PATH,
        str(seed_env_id)
    )
    shutil.copytree(source_env_keys_path, seed_env_keys_path)


def get_generated(env_id):
    return environment_obj.Environment.connection.get_request(
        'clusters/{0}/generated'.format(env_id))
