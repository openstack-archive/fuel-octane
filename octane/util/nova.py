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
import time

from octane import magic_consts
from octane.util import helpers
from octane.util import node as node_util

LOG = logging.getLogger(__name__)


class WaiterException(Exception):

    message = "After {attempts} tries of checking instances on {hostname}" \
              "some instances are still in {status} status"

    def __init__(self, hostname, attempts, status):
        msg = self.message.format(
            hostname=hostname, attempts=attempts, status=status)
        super(Exception, self).__init__(msg)


def do_nova_instances_exist(controller, node_fqdn, status=None):
    cmd = ['nova', 'list', '--host', node_fqdn, '--limit', '1', '--minimal']
    if status:
        cmd += ['--status', status]
    result = node_util.run_with_openrc(cmd, controller)
    return bool(helpers.parse_table_output(result))


def waiting_for_status_completed(controller, node_fqdn, status,
                                 attempts=180, attempt_delay=10):
    for iteration in xrange(attempts):
        LOG.info(
            "Waiting until instances on {hostname} hostname "
            "exists in {status} (iteration {iteration})".format(
                hostname=node_fqdn, status=status, iteration=iteration))
        if do_nova_instances_exist(controller, node_fqdn, status):
            time.sleep(attempt_delay)
        else:
            return
    raise WaiterException(node_fqdn, attempts, status)


def get_compute_lists(controller):
    """return tuple of lists enabled and disabled computes"""
    service_stdout = node_util.run_with_openrc(
        ["nova", "service-list", "--binary", "nova-compute"], controller)
    parsed_service_list = helpers.parse_table_output(service_stdout)
    enabled_computes = []
    disabled_computes = []
    for service in parsed_service_list:
        if service['Status'] == 'enabled':
            enabled_computes.append(service['Host'])
        elif service['Status'] == 'disabled':
            disabled_computes.append(service['Host'])
    return (enabled_computes, disabled_computes)


def get_active_instances(controller, node_fqdn):
    instances_stdout = node_util.run_with_openrc([
        "nova", "list",
        "--host", node_fqdn,
        "--limit", "-1",
        "--status", "ACTIVE",
        "--minimal"],
        controller)
    instances = helpers.parse_table_output(instances_stdout)
    return [i["ID"] for i in instances]


def get_upgrade_levels(version):
    try:
        release = magic_consts.UPGRADE_LEVELS[version]
    except KeyError:
        LOG.error("Could not find suitable upgrade_levels for the "
                  "{version} release.".format(version=version))
        raise
    else:
        return release
