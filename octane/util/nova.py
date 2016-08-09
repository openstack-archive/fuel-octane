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
import shlex
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


def nova_stdout_parser(cmd_stdout):
    """Parse nova cmd stdout

    Return list of dicts ther keys are the header of the cmd out table.
    """
    results = []
    headers = None
    for line in cmd_stdout.splitlines():
        lex = shlex.shlex(line, posix=True)
        lex.whitespace_split = True
        lex.commenters = '+'
        lex.whitespace += "|"
        lex_list = list(lex)
        if not lex_list:
            continue
        if headers is None:
            headers = lex_list
        else:
            results.append(dict(zip(headers, lex_list)))
    return results


def do_nova_instances_exist(controller, node_fqdn, status=None):
    cmd = [
        'nova', 'list', '--host', node_fqdn, '--limit', '1', '--minimal']
    if status:
        cmd += ['--status', status]
    result = run_nova_cmd(cmd, controller)
    return bool(nova_stdout_parser(result))


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
    service_stdout = run_nova_cmd(
        ["nova", "service-list", "--binary", "nova-compute"], controller, True)
    parsed_service_list = nova_stdout_parser(service_stdout)
    enabled_computes = []
    disabled_computes = []
    for service in parsed_service_list:
        if service['Status'] == 'enabled':
            enabled_computes.append(service['Host'])
        elif service['Status'] == 'disabled':
            disabled_computes.append(service['Host'])
    return (enabled_computes, disabled_computes)
