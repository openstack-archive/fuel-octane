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
import os
import sys
import uuid

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane.util import ssh as ssh_util

LOG = logging.getLogger(__name__)


def check_sudo(env_id, node_ids):
    if os.environ['use_sudo'] == 'False':
        LOG.error("Did you forget to pass --sudo ???")
        sys.exit(1)

    env = environment_obj.Environment(env_id)
    nodes = [node_obj.Node(n) for n in node_ids]
    if len(nodes) == 0:
        # If no nodes were passed, we'll test every node.
        for node in node_obj.Node.get_all():
            if node.data['cluster'] == env.data['id']:
                nodes.append(node)

    test_cmd = ['whoami']
    test_file = '/root/octane-%s' % uuid.uuid4()
    oks = []
    errors = []
    for node in nodes:
        sudo_ok = False
        sftp_ok = False
        try:
            output = ssh_util.call_output(test_cmd, node=node).strip()
            if output == "root":
                sudo_ok = True
            else:
                msg = "node %s: sudo failed: whoami: %s" % \
                      (node.data['hostname'], output)
                LOG.error(msg)
        except Exception as err:
            msg = "node %s: %s" % (node.data['hostname'], err)
            errors.append(msg)
            LOG.error(msg)

        # If sudo failed, no point in testing SFTP.
        if sudo_ok:
            try:
                sftp = ssh_util.sftp(node=node)
                with sftp.file(test_file, 'w') as fp:
                    fp.write('testing')
                sftp.unlink(test_file)
                sftp_ok = True
            except Exception as err:
                msg = "node %s: %s" % (node.data['hostname'], err)
                errors.append(msg)
                LOG.error(err)

        if sudo_ok and sftp_ok:
            msg = "node %s sudo/SFTP OK." % node.data['hostname']
            oks.append(msg)
            LOG.info(msg)

    LOG.info("------ Node summary ------")
    for msg in oks:
        LOG.info(msg)
    if len(errors) > 0:
        LOG.error("Some nodes failed:")
        for msg in errors:
            LOG.error(msg)


class CheckSudoCommand(cmd.Command):
    """Tests that SSH and sudo access are available for each node."""

    def get_parser(self, prog_name):
        parser = super(CheckSudoCommand, self).get_parser(prog_name)
        parser.add_argument(
            'env_id', type=int,
            help="ID of environment to test")
        parser.add_argument(
            'node_ids', type=int, nargs='*', default=[],
            help="ID of environment to test")
        return parser

    def take_action(self, parsed_args):
        check_sudo(parsed_args.env_id, parsed_args.node_ids)
