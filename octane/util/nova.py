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

from octane.util import ssh

LOG = logging.getLogger(__name__)


class WaiterException(Exception):

    message = "After {attempts} tries of checking instances on {hostname}" \
              "some instances are still in {status} status"

    def __init__(self, hostname, attempts, status):
        msg = self.message.format(
            hostname=hostname, attempts=attempts, status=status)
        super(Exception, self).__init__(msg)


def run_nova_cmd(cmd, node, output=True):
    run_cmd = ['sh', '-c', ' '.join(['.', '/root/openrc;'] + cmd)]
    if output:
        return ssh.call_output(run_cmd, node=node)
    return ssh.call(run_cmd, node=node)


def do_nova_instances_exist_in_status(controller, node_fqdn, status):
    result = run_nova_cmd(['nova', 'list',
                           '--host', node_fqdn,
                           '--status', status,
                           '--limit', '1',
                           '--minimal'], controller)
    return len(result.strip().splitlines()) != 4


def waiting_for_status_completed(controller, node_fqdn, status,
                                 attempts=180, attempt_delay=10):
    for iteration in xrange(attempts):
        LOG.info(
            "Waiting until migration ends on {0} "
            "hostname (iteration {1})".format(node_fqdn, iteration))
        if do_nova_instances_exist_in_status(controller, node_fqdn, status):
            time.sleep(attempt_delay)
        else:
            return
    raise WaiterException(node_fqdn, attempts, status)
