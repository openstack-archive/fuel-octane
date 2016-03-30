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
import tempfile

from cliff import command as cmd

from fuelclient.objects import node as node_obj

from octane.handlers import backup_restore
from octane import magic_consts
from octane.util import fuel_client
from octane.util import helpers
from octane.util import ssh

LOG = logging.getLogger(__name__)


def _get_backup_path(path):
    return tempfile.mkstemp(suffix=".bak",
                            dir=os.path.dirname(path),
                            prefix='{0}.'.format(os.path.basename(path)))[1]


def upgrade_osd(env_id, user, password):
    with fuel_client.set_auth_context(
            backup_restore.NailgunCredentialsContext(user, password)):
        nodes = [n for n in node_obj.Node.get_all()
                 if "ceph-osd" in n.data["roles"]]
    if not nodes:
        LOG.info("Nothing to upgrade")
        return
    backup_val = [
        # (node, path, backup_path)
    ]
    admin_ip = helpers.get_astute_dict()["ADMIN_NETWORK"]["ipaddress"]
    try:
        hostnames = []
        for node in nodes:
            sftp = ssh.sftp(node)
            for path, content in magic_consts.OSD_REPOS_UPDATE:
                back_path = _get_backup_path(path)
                ssh.call(["cp", path, back_path], node=node)
                backup_val.append((node, path, back_path))
                with ssh.update_file(sftp, path) as (_, new):
                    new.write(content.format(admin_ip=admin_ip))
            hostnames.append(node.data["hostname"])
            ssh.call(["dpkg", "--configure", "-a"], node=node)
        call_node = nodes[0]
        ssh.call(["ceph", "osd", "set", "noout"], node=call_node)
        ssh.call(['ceph-deploy', 'install', '--release', 'hammer'] + hostnames,
                 node=call_node, stdout=ssh.PIPE, stderr=ssh.PIPE)
        for node in nodes:
            ssh.call(["restart", "ceph-osd-all"], node=node)
        ssh.call(["ceph", "osd", "unset", "noout"], node=call_node)
        ssh.call(["ceph", "osd", "stat"], node=call_node)
    finally:
        for node, path, back_path in backup_val:
            ssh.call(["mv", back_path, path], node=node)
        for node in nodes:
            ssh.call(["dpkg", "--configure", "-a"], node=node)


class UpgradeOSDCommand(cmd.Command):
    """Upgrade osd servers"""

    def get_parser(self, prog_name):
        parser = super(UpgradeOSDCommand, self).get_parser(prog_name)
        parser.add_argument(
            'env_id', type=int, metavar='ENV_ID',
            help="ID of target environment")
        parser.add_argument(
            "--admin-password",
            type=str,
            action="store",
            dest="admin_password",
            required=True,
            help="Fuel admin password")
        return parser

    def take_action(self, parsed_args):
        upgrade_osd(parsed_args.env_id, 'admin', parsed_args.admin_password)
