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

import functools
import shutil
import socket
import sys
import time

from oslo_log import log as logging

from distutils import version
from octane.util import helpers
from octane.util import ssh

LOG = logging.getLogger(__name__)


def preserve_partition(node, partition):
    disks = node.get_attribute('disks')
    for disk in disks:
        for vol in disk['volumes']:
            if vol['name'] == partition:
                vol.update({
                    'keep': True,
                    'keep_data': True,
                })

    node.upload_node_attribute('disks', disks)


def get_ip(network_name, node):
    for net in node.data['network_data']:
        if net['name'] == network_name:
            return net['ip']


def get_ips(network_name, nodes):
    get_network_ip = functools.partial(get_ip, network_name)
    return map(get_network_ip, nodes)


def get_hostnames(nodes):
    return [node.data['fqdn'] for node in nodes]


def tar_files(filename, node, *files):
    cmd = ['tar', '-czvP']
    cmd.extend(files)
    with ssh.popen(cmd, stdout=ssh.PIPE, node=node) as proc:
        with open(filename, 'wb') as f:
            shutil.copyfileobj(proc.stdout, f)


def untar_files(filename, node):
    cmd = ['tar', '-xzv', '-C', '/']
    with ssh.popen(cmd, stdin=ssh.PIPE, node=node) as proc:
        with open(filename, 'rb') as f:
            shutil.copyfileobj(f, proc.stdin)


def get_hostname_remotely(node):
    hostname = ssh.call_output(['hostname'], node=node)
    return hostname[:-1]


def get_nova_node_handle(node):
    version_num = node.env.data.get('fuel_version')
    if not version_num:
        raise Exception("Cannot determine Fuel version for node {0}"
                        .format(node.data['id']))
    if version.StrictVersion(version_num) < version.StrictVersion('6.1'):
        return "node-{0}".format(node.data['id'])
    return node.data['fqdn']


def reboot_nodes(nodes, timeout=600):
    old_clients = dict((node, ssh.get_client(node)) for node in nodes)
    for node in nodes:
        ssh.call(['reboot'], node=node)
    node_ids_str = ", ".join(str(node.data['id']) for node in nodes)
    LOG.debug("Sent reboot command to nodes: %s", node_ids_str)
    wait_list = set(nodes)
    start = time.time()
    while wait_list:
        time.sleep(10)
        done = set()
        for node in wait_list:
            if time.time() - start > timeout:
                failed = ", ".join(str(node.data['id']) for node in wait_list)
                raise Exception(
                    "Timeout waiting for nodes {0} to reboot".format(
                        failed))
            try:
                new_client = ssh.get_client(node)
            except socket.error:
                LOG.debug("Failed to connect to node %s", node.data['id'],
                          exc_info=sys.exc_info())
                node.update()  # IP could've been changed, use new IP next time
                continue
            if new_client != old_clients[node]:
                done.add(node)
        wait_list -= done


def wait_for_mcollective_start(nodes, timeout=600):
    start_at = time.time()
    wait_list = set(nodes)
    node_ids_str = ", ".join(str(node.data['id']) for node in nodes)
    LOG.info("Wait for mcollective start on nodes {0}".format(node_ids_str))
    while wait_list:
        time.sleep(10)
        done = set()
        for node in wait_list:
            try:
                ssh.call(['service', 'mcollective', 'status'], node=node)
            except Exception as e:
                LOG.debug(e)
            else:
                done.add(node)
        if time.time() - start_at > timeout:
            failed = ", ".join(str(node.data['id'] for node in wait_list))
            raise Exception("Timeout waiting for nodes {0} to start"
                            " mcollective".format(failed))
        wait_list -= done


def add_compute_upgrade_levels(node, version):
    sftp = ssh.sftp(node)
    with ssh.update_file(sftp, '/etc/nova/nova.conf') as (old, new):
        add_upgrade_levels = True
        in_section = False
        for line in old:
            if line.startswith("[upgrade_levels]"):
                add_upgrade_levels = False
                in_section = True
                new.write(line)
                new.write("compute={0}\n".format(version))
                continue
            if in_section and line.startswith("["):
                in_section = False
            if in_section and line.startswith("compute="):
                LOG.warning(
                    "Skipping line so not to duplicate compute "
                    "upgrade level setting: %s" % line.rstrip())
                continue
            new.write(line)
        if add_upgrade_levels:
            new.write("[upgrade_levels]\ncompute={0}\n".format(version))


def remove_compute_upgrade_levels(node):
    sftp = ssh.sftp(node)
    with ssh.update_file(sftp, '/etc/nova/nova.conf') as (old, new):
        for line in old:
            if line.startswith("compute="):
                continue
            new.write(line)


def is_live_migration_supported(node):
    sftp = ssh.sftp(node)
    with sftp.open('/etc/nova/nova.conf') as config:
        for line in config:
            if line.strip().startswith("live_migration_flag") \
                    and "VIR_MIGRATE_LIVE" in line:
                return True
    return False


def restart_nova_services(node):
    nova_services = ssh.call_output(["service", "--status-all"], node=node)
    for service_line in nova_services.splitlines():
        service_line = service_line.strip()
        _, status, _, service = service_line.split()
        if status == "+" and service.startswith("nova"):
            ssh.call(["service", service, "restart"], node=node)


class AbsentParametersError(Exception):
    msg = "Could not get parameters from the file " \
          "node-{node_id}[{filename}]: {parameters}"

    def __init__(self, node_id, filename, parameters):
        super(AbsentParametersError, self).__init__(self.msg.format(
            node_id=node_id,
            filename=filename,
            parameters=", ".join(parameters),
        ))


def get_parameters(node, filename, parameters_to_get, ensure=True):
    with ssh.sftp(node).open(filename) as fp:
        parameters = helpers.get_parameters(fp, parameters_to_get)
    if ensure:
        required_parameters = set(parameters_to_get)
        current_parameters = set(parameters)
        absent_parameters = required_parameters - current_parameters
        if absent_parameters:
            flat_parameters = []
            for aparam in absent_parameters:
                for param in parameters_to_get[aparam]:
                    flat_parameters.append("/".join(param))
            raise AbsentParametersError(
                node.data["id"], filename, flat_parameters)
    return parameters


def restart_mcollective(node):
    node_id = node.data["id"]
    if not node.data["online"]:
        LOG.warning("Not possible to restart mcollective on the offline "
                    "node %s", node_id)
        return None
    try:
        ssh.call(["service", "mcollective", "restart"], node=node)
    except Exception as exc:
        LOG.warning("Failed to restart mcollective on the node %s: %s",
                    node_id, exc)
        return False
    else:
        LOG.info("The mcollective service was successfully restarted on "
                 "the node %s", node_id)
        return True
