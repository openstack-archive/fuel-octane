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
from octane.util import helpers
from octane.util import ssh

LOG = logging.getLogger(__name__)


def check_sanity(nodes, release):
    if release.data['state'] != 'available':
        raise Exception(
            "Release with id {0} is not available.".format(release.id)
        )

    env_id = nodes[0].env.id
    for node in nodes:
        if node.env.id != env_id:
            raise Exception(
                "Nodes have different clusters."
            )
        env_id = node.env.id
        if 'compute' not in node.data['roles']:
            raise Exception(
                "Preupgrade procedure is available only for compute nodes. "
                "Node with id {0} is not a compute.".format(node.id)
            )


def change_repositories(node, repos):
    ssh.remove_all_files_from_dirs(['/etc/apt/sources.list.d/',
                                    '/etc/apt/preferences.d/'], node)
    sftp = ssh.sftp(node)
    for repo in repos:
        filename_source, content_source = apt.create_repo_source(repo)
        ssh.write_content_to_file(sftp, filename_source, content_source)
        filename_pref, content_pref = apt.create_repo_preferences(repo)
        ssh.write_content_to_file(sftp, filename_pref, content_pref)
    ssh.call(['apt-get', 'update'], node=node)


def stop_compute_services(node):
    ssh.call(['stop', 'nova-compute'], node=node)
    ssh.call(['stop', 'neutron-plugin-openvswitch-agent'], node=node)


def get_repos(release, master_ip=''):
    repos = (release.data['attributes_metadata']['editable']['repo_setup']
             ['repos']['value'])

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


def preupgrade_compute(node_ids, release_id):
    nodes = [objects.node.Node(node_id) for node_id in node_ids]
    release = objects.Release(release_id)
    check_sanity(nodes, release)
    master_ip = helpers.get_astute_dict()["ADMIN_NETWORK"]['ipaddress']

    version = release.data['version']
    repos = get_repos(release, master_ip)
    packages = magic_consts.COMPUTE_PREUPGRADE_PACKAGES.get(version)
    for node in nodes:
        change_repositories(node, repos)
        stop_compute_services(node)
        apt.upgrade_packages(node, packages)


class PreupgradeComputeCommand(cmd.Command):
    """Preupgrade compute"""

    def get_parser(self, prog_name):
        parser = super(PreupgradeComputeCommand, self).get_parser(prog_name)
        parser.add_argument(
            'release-id',
            type=int,
            metavar='RELEASE_ID',
            help="Release that repositories will be taken from"
        )
        parser.add_argument(
            'node_ids',
            type=int,
            metavar='NODE_ID',
            help="IDs of compute nodes to be preupgraded",
            nargs="+")
        return parser

    def take_action(self, parsed_args):
        preupgrade_compute(parsed_args.release_id, parsed_args.node_ids)
