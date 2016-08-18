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
import collections
import logging

from cliff import command as cmd

from fuelclient import objects

from octane import magic_consts
from octane.util import apt
from octane.util import env as env_obj
from octane.util import ssh

LOG = logging.getLogger(__name__)


def change_repositories(node, repos):
    for repo in repos:
        filename_source, content_source = apt.create_repo_source(repo)
        write_new_content(filename_source, content_source, node)
        filename_pref, content_pref = apt.create_repo_preferences(repos)
        write_new_content(filename_pref, content_pref, node)
    ssh.call(['apt-get', 'update'], node=node)


def write_new_content(filename, content, node):
    sftp = ssh.sftp(node)
    with ssh.update_file(sftp, filename) as (old, new):
        new.writeline(content)


def stop_compute_services(node):
    ssh.call(['stop', 'nova-compute'], node=node)
    ssh.call(['stop', 'neutron-plugin-openvswitch-agent'], node=node)


def get_repos(release, master_ip=''):
    repos = release.data['attributes_metadata']['editable']['repo_setup']
    ['repos']['value']

    version = release.data['version']
    environment_version = version.split('-')[1]

    settings_cls = collections.namedtuple("settings", ["MASTER_IP", "release"])
    release_cls = collections.namedtuple("release",
                                         ["version", "environment_version"])
    settings = settings_cls(master_ip,
                            release_cls(version, environment_version))
    for repo in repos:
        repo['uri'] = repo['uri'].format(settings=settings, cluster=settings)
    return repos


def upgrade_compute(node_ids, release_id):
    nodes = [objects.node.Node(node_id) for node_id in node_ids]
    env = nodes[0].env
    master_ip = env_obj.get_astute_yaml(env)['master_ip']
    release = objects.Release(release_id)
    version = release.data['version']
    repos = get_repos(release, master_ip)
    packages = magic_consts.COMPUTE_PREUPGRADE_PACKAGES.get(version)
    for node in nodes:
        change_repositories(node, repos)
        stop_compute_services(node)
        apt.upgrade_packages(node, packages)


class UpgradeComputeCommand(cmd.Command):
    """Upgrade osd servers"""

    def get_parser(self, prog_name):
        parser = super(UpgradeComputeCommand, self).get_parser(prog_name)
        parser.add_argument(
            'node_ids',
            type=int,
            metavar='NODE_ID',
            help="ID of target environment",
            nargs="+")
        parser.add_arguemnt(
            '--release-id',
            type=int,
            help="Release that repositories will be taken from"
        )
        return parser

    def take_action(self, parsed_args):
        upgrade_compute(parsed_args.node_ids, parsed_args.release_id)
