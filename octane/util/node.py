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

import logging
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


def set_reinstall_node_flag(env, node):
    # It should be safe to work with single node deployment info as we don't
    # support upgrade of multiple ceph-osd nodes at once.
    deployment_info = env.get_default_facts('deployment',
                                            nodes=[node.data['id']])
    for info in deployment_info:
        info.update({'reinstall_node': 'true'})
    env.upload_facts('deployment', deployment_info)
