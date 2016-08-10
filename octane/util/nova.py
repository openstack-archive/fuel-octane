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

import shlex

from octane.util import ssh


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


def do_nova_instances_exist_in_status(controller, node_fqdn, status):
    result = run_nova_cmd(['nova', 'list',
                           '--host', node_fqdn,
                           '--status', status,
                           '--limit', '1',
                           '--minimal'], controller)
    return bool(nova_stdout_parser(result))
