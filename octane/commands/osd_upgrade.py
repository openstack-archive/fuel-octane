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
import json
import logging
import os
import time

from cliff import command as cmd

from fuelclient.objects import environment as env_obj

from octane.handlers import backup_restore
from octane import magic_consts
from octane.util import env
from octane.util import fuel_client
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


def generate_source_content(repos):
    return '\n'.join([magic_consts.OSD_UPGRADE_SOURCE_TEMPLATE.format(**repo)
                      for repo in repos])


def generate_preference_pin(repos, priority):
    packages = " ".join(magic_consts.OSD_UPGRADE_REQUIRED_PACKAGES)
    contents = []
    for repo in repos:
        suite = repo['suite']
        contents.append(
            magic_consts.OSD_UPGADE_PREFERENCE_TEMPLATE.format(
                packages=packages,
                suite=suite,
                priority=priority
            ))
    return '\n'.join(contents)


def apply_source_for_node(node, content):
    return write_content_to_tmp_file_on_node(
        node, content, "/etc/apt/sources.list.d/", "mos.osd_XXX.list")


def apply_preference_for_node(node, content):
    return write_content_to_tmp_file_on_node(
        node, content, "/etc/apt/preferences.d/", "mos.osd_XXX.pref")


def get_env_repos(env):
    return env.get_attributes()['editable']['repo_setup']['repos']['value']


def get_repo_highest_priority(env):
    return max([i['priority'] for i in get_env_repos(env)]) or 0


@contextlib.contextmanager
def applied_repos(nodes, preference_priority, seed_repos):
    node_file_to_clear_list = []
    preference_content = generate_preference_pin(
        seed_repos, preference_priority)
    source_content = generate_source_content(seed_repos)
    try:
        for node in nodes:
            node_file_to_clear_list.append(
                (node, apply_preference_for_node(node, preference_content)))
            node_file_to_clear_list.append(
                (node, apply_source_for_node(node, source_content)))
        yield
    finally:
        for node, file_name_to_remove in node_file_to_clear_list:
            sftp = ssh.sftp(node)
            sftp.unlink(file_name_to_remove)


def get_current_versions(controller, kind):
    stdout = ssh.call_output(
        ['ceph', 'tell', '{0}.*'.format(kind), 'version', '-f', 'json'],
        node=controller)
    results = []
    for line in stdout.splitlines():
        if not line:
            continue
        if line.startswith(kind):
            line = line.split(":", 1)[1]
        results.append(json.loads(line))
    return {v['version'] for v in results}


def is_same_versions_on_mon_and_osd(controller):
    mons = get_current_versions(controller, "mon")
    osds = get_current_versions(controller, "osd")
    is_equal = mons == osds
    if not is_equal:
        LOG.info("Installed MONs versions: {0} and OSDs versions: {1}".format(
            ' '.join(mons), ' '.join(osds)))
    return is_equal


def is_ceph_up(controller):
    stdout = ssh.call_output(['ceph', 'osd', 'tree', '-f', 'json'],
                             node=controller)
    data = json.loads(stdout.strip())
    return all(n['status'] == 'up' for n in data['nodes']
               if n['type'] == 'osd')


def waiting_until_ceph_up(controller, delay=5, times=30):
    for _ in xrange(times):
        if is_ceph_up(controller):
            return
        time.sleep(delay)
    raise Exception(
        "After upgrade not all ceph osd nodes ar UP after {0} seconds".format(
            delay * times))


def upgrade_osd(orig_env_id, seed_env_id, user, password):
    with fuel_client.set_auth_context(
            backup_restore.NailgunCredentialsContext(user, password)):
        orig_env = env_obj.Environment(orig_env_id)
        nodes = list(env.get_nodes(orig_env, ["ceph-osd"]))
        seed_env = env_obj.Environment(seed_env_id)
        seed_repos = get_env_repos(seed_env)
        preference_priority = get_repo_highest_priority(orig_env)
    if not nodes:
        LOG.info("Nothing to upgrade")
        return
    controller = env.get_one_controller(seed_env)
    if is_same_versions_on_mon_and_osd(controller):
        LOG.warn("MONs and OSDs have the same version, nothing to upgrade.")
        return
    hostnames = [n.data['hostname'] for n in nodes]
    with applied_repos(nodes, preference_priority + 1, seed_repos):
        call_node = nodes[0]
        ssh.call(["ceph", "osd", "set", "noout"], node=call_node)
        ssh.call(['ceph-deploy', 'install', '--release', 'hammer'] + hostnames,
                 node=call_node)
    for node in nodes:
        ssh.call(["restart", "ceph-osd-all"], node=node)
    ssh.call(["ceph", "osd", "unset", "noout"], node=call_node)
    waiting_until_ceph_up(controller)
    if not is_same_versions_on_mon_and_osd(controller):
        msg = "OSDs not upgraded up to MONs version, please fix the problem"
        LOG.error(msg)
        raise Exception(msg)


class UpgradeOSDCommand(cmd.Command):
    """Upgrade osd servers"""

    def get_parser(self, prog_name):
        parser = super(UpgradeOSDCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_env_id',
            type=int,
            metavar='ORIG_ENV_ID',
            help="ID of orig environment")
        parser.add_argument(
            'seed_env_id',
            type=int,
            metavar='SEED_ENV_ID',
            help="ID of seed environment")
        parser.add_argument(
            "--admin-password",
            type=str,
            action="store",
            dest="admin_password",
            required=True,
            help="Fuel admin password")
        return parser

    def take_action(self, parsed_args):
        upgrade_osd(
            parsed_args.orig_env_id,
            parsed_args.seed_env_id,
            'admin',
            parsed_args.admin_password)
