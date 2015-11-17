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
import logging
import shutil
import socket
import sys
import time

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
