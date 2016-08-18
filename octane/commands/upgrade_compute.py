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

from cliff import command as cmd

from fuelclient import objects


from octane import magic_consts
from octane.util import env
from octane.util import ssh

LOG = logging.getLogger(__name__)

COMPUTE_PREUPGRADE_PACKAGES = {
    'liberty-8.0': [
        "python-routes", "python-oslo.concurrency", "python-sqlparse",
        "nova-common", "python-pkg-resources", "python-oslo.policy",
        "neutron-plugin-ml2", "python-oslo.config", "python-glanceclient",
        "python-paramiko", "python-jinja2", "python-nova" "python-editor",
        "python-contextlib2", "libvirt-clients", "python-oslo.serialization"
        "python-urllib3", "python-keystonemiddleware", "python-openssl",
        "libvirt0","fuel-ha-utils", "python-netaddr", "python-oslo.i18n",
        "python- cliff", "python-oslo.reports", "python-libvirt",
        "neutron-common", "python-oslo.versionedobjects", "python-oslo.db",
        "nailgun-mcagents", "python-novaclient", "python-unicodecsv",
        "neutron-plugin-openvswitch-agent", "python-oslo.rootwrap",
        "python-oslo.utils", "python-ipaddress", "python-oslo.lo",
        "python-msgpack", "python-amqp", "python-cryptography", "python-six",
        "python-oslo.context", "python-openvswitch", "python-netifaces",
        "libvirt-daemon", "network-checker", "python-oslo.messaging",
        "mcollective-common", "python-oslo.middleware", "python-jsonschema"
        "python-keystoneclient", "python-oslo.service", "python-neutronclient",
        "python-requests", "python-singledispatch", "python-neutron",
        "python-stevedore", "python-sqlalchemy", "nova-compute",
        "nova-compute-qemu", "python-extras", "mcollective", "libvirt-bin"
        "python-cinderclient", "python-concurrent.futures"
    ]
}


def default_preupgrade_release(env):
    raise NotImplemented


def change_repositories(node, release):
    remove_old_source(node)
    sourses = magic_consts.COMPUTE_SOURSES
    write_new_sources(sourses, node)
    ssh.call(['apt-get', 'update'], node=node)


def remove_old_source(node):
    ssh.call(['rm', '-rf',   magic_consts.SOURCES_PATH])


def write_new_sources(sourses, node):
    sftp = ssh.sftp(node)
    with ssh.update_file(sftp, magic_consts.SOURSES_LIST) as (old, new):
        new.writelines(sourses)


def stop_compute_services(node):
    ssh.call(['stop', 'nova-compute'], node=node)
    ssh.call(['stop', 'neutron-plugin-openvswitch-agent'], node=node)


def upgrade_packages(node, packages):
    noninteractive = 'DEBIAN_FRONTEND=noninteractive'
    ssh.call(
        [noninteractive, 'apt-get', 'install', '--only-upgrade', '-y',
         '-o', 'Dpkg::Options::="--force-confold"', '--force-yes'] + packages,
        node=node
    )


def upgrade_compute(node_ids, release_id):

    nodes = [objects.node.Node(node_id) for node_id in node_ids]
    env = nodes[0].env
    if release_id is None:
        release_id = default_preupgrade_release(env)
    release = objects.Release(release_id)
    version = release.data['version']
    packages = COMPUTE_PREUPGRADE_PACKAGES.get(version)

    for node in nodes:
        change_repositories(node, release)
        stop_compute_services(node)
        upgrade_packages(node, packages)


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
