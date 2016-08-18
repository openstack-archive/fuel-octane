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

import contextlib
import logging
import os

from cliff import command as cmd

from fuelclient.objects import environment as env_obj

from octane.handlers import backup_restore
from octane import magic_consts
from octane.util import env
from octane.util import fuel_client
from octane.util import helpers
from octane.util import ssh

LOG = logging.getLogger(__name__)


def _get_backup_path(path, node):
    dir_name = os.path.dirname(path)
    prefix_name = os.path.basename(path)
    return ssh.call_output(
        [
            "tempfile",
            "-d", dir_name,
            "-p", ".{0}".format(prefix_name),
            "-s", ".bak",
        ],
        node=node)


def write_content_to_tmp_file_on_node(node, content, directory, template):
    tmp_name = ssh.call_output(
        ["mktemp", "-p", directory, "-t", template], node=node).strip()
    sftp = ssh.sftp(node)
    with sftp.open(tmp_name, "w") as new:
        new.write(content)
    return tmp_name


@contextlib.contextmanager
def applied_repos(nodes, preference_priority):
    admin_ip = helpers.get_astute_dict()["ADMIN_NETWORK"]["ipaddress"]
    packages = " ".join(magic_consts.OSD_UPGRADE_REQUIRED_PACKAGES)
    preference_content = magic_consts.OSD_UPGADE_PREFERENCE_TEMPLATE.format(
        packages=packages, priority=preference_priority)
    source_content = magic_consts.OSD_UPGRADE_SOURCE_TEMPLATE.format(
        admin_ip=admin_ip)

    node_file_to_clear_list = []
    try:
        for node in nodes:
            source = write_content_to_tmp_file_on_node(
                node, source_content,
                "/etc/apt/sources.list.d/", "mos.osd_XXX.list")
            node_file_to_clear_list.append((node, source))
            preference = write_content_to_tmp_file_on_node(
                node, preference_content,
                "/etc/apt/preferences.d/", "mos.osd_XXX.pref")
            node_file_to_clear_list.append((node, preference))
        yield
    finally:
        for node, file_name_to_remove in node_file_to_clear_list:
            sftp = ssh.sftp(node)
            sftp.unlink(file_name_to_remove)


def get_repo_highest_priority(orig_env):
    editable = orig_env.get_attributes()['editable']
    repos = editable['repo_setup']['repos']['value']
    return max([i['priority'] for i in repos])


def upgrade_osd(env_id, user, password):
    with fuel_client.set_auth_context(
            backup_restore.NailgunCredentialsContext(user, password)):
        orig_env = env_obj.Environment(env_id)
        nodes = list(env.get_nodes(orig_env, ["ceph-osd"]))
    if not nodes:
        LOG.info("Nothing to upgrade")
        return
    preference_priority = get_repo_highest_priority(orig_env)
    hostnames = [n.data['hostname'] for n in nodes]
    with applied_repos(nodes, preference_priority + 1):
        call_node = nodes[0]
        ssh.call(["ceph", "osd", "set", "noout"], node=call_node)
        ssh.call(['ceph-deploy', 'install', '--release', 'hammer'] + hostnames,
                 node=call_node)
    for node in nodes:
        ssh.call(["restart", "ceph-osd-all"], node=node)
    ssh.call(["ceph", "osd", "unset", "noout"], node=call_node)


class UpgradeOSDCommand(cmd.Command):
    """Upgrade osd servers"""

    def get_parser(self, prog_name):
        parser = super(UpgradeOSDCommand, self).get_parser(prog_name)
        parser.add_argument(
            'env_id',
            type=int,
            metavar='ENV_ID',
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
