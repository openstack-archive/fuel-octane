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
from cliff import command as cmd
from fuelclient.objects import environment as environment_obj

from octane.util import ceph
from octane.util import env as env_util
from octane.util import maintenance
from octane.util import network
from octane.util import ssh


def upgrade_osd(orig_env, seed_env):
    nodes = list(env_util.get_nodes(orig_env, ['ceph-osd', 'compute']))
    osds = [n for n in nodes if 'ceph-osd' in n.data['roles']]
    if not osds:
        return
    seed_controller = env_util.get_one_controller(seed_env)
    ssh.call(["ceph", "osd", "set", "noout"], node=osds[0])
    ssh.call(["ceph", "osd", "set", "noout"], node=seed_controller)
    ceph_conf_file = ceph.get_ceph_conf_filename(seed_controller)
    ceph_conf = ssh.call_output(['cat', ceph_conf_file], node=seed_controller)

    for node in nodes:
        sftp = ssh.sftp(node)
        with ssh.update_file(sftp, ceph_conf_file) as (_, new):
            new.write(ceph_conf)
    for osd in osds:
        ssh.call(["restart", "ceph-osd-all"], node=osd)
    # controllers and osd in same env now
    ssh.call(["ceph", "osd", "unset", "noout"], node=osds[0])


def upgrade_control_plane(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    controllers = list(env_util.get_controllers(seed_env))
    # enable all services on seed env
    if len(controllers) > 1:
        maintenance.stop_cluster(seed_env)
    else:
        maintenance.start_corosync_services(seed_env)
        maintenance.start_upstart_services(seed_env)
    upgrade_osd(orig_env, seed_env)
    # disable cluster services on orig env
    maintenance.stop_cluster(orig_env)
    # switch networks to seed env
    roles = ['primary-controller', 'controller']
    # disable physical connectivity for orig env
    for node, info in env_util.iter_deployment_info(orig_env, roles):
        network.delete_patch_ports(node, info)
    # enable physical connectivity for seed env
    for node, info in env_util.iter_deployment_info(seed_env, roles):
        network.delete_overlay_networks(node, info)
        network.create_patch_ports(node, info)
    # enable all services on seed env
    if len(controllers) > 1:
        maintenance.start_cluster(seed_env)
        maintenance.start_corosync_services(seed_env)
        maintenance.start_upstart_services(seed_env)


class UpgradeControlPlaneCommand(cmd.Command):
    """Switch control plane to the seed environment"""

    def get_parser(self, prog_name):
        parser = super(UpgradeControlPlaneCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        return parser

    def take_action(self, parsed_args):
        upgrade_control_plane(parsed_args.orig_id, parsed_args.seed_id)
