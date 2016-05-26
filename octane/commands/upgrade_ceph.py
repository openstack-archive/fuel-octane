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
import itertools
import os
import re
import subprocess
import tarfile

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj

from octane import magic_consts
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import ssh


def short_hostname(hostname):
    return hostname.partition('.')[0]


def remove_mask(ip_addr):
    return ip_addr.partition('/')[0]


def replace_addresses(conf, hostnames, mgmt_ips):
    mon_initial_members = ' '.join(hostnames)
    mon_host = ' '.join(mgmt_ips)

    conf = re.sub(r'\n(mon_initial_members\s+=\s+)[-.\w\s]*\n',
                  "\n\g<1>{0}\n".format(mon_initial_members),
                  conf)
    conf = re.sub(r'\n(mon_host\s+=\s+)[-.\w\s]*\n',
                  "\n\g<1>{0}\n".format(mon_host),
                  conf)
    return conf


def get_fsid(conf):
    match = re.search(r'\nfsid\s+=\s+([-.\w]+)\s*\n', conf)
    if match is not None:
        return match.group(1)


def replace_host(conf, hostname):
    conf = re.sub(r'\n(host\s+=\s+)[-.\w\s]*\n',
                  "\n\g<1>{0}\n".format(hostname),
                  conf)
    return conf


def import_bootstrap_osd(node):
    ssh.call(['ceph', 'auth', 'import', '-i',
              '/root/ceph.bootstrap-osd.keyring'], node=node)
    ssh.call(['ceph', 'auth', 'caps', 'client.bootstrap-osd', 'mon',
              "allow profile bootstrap-osd"], node=node)


def get_ceph_conf_filename(node):
    cmd = [
        'bash', '-c',
        'pgrep ceph-mon | xargs -I{} cat /proc/{}/cmdline',
    ]
    cmdlines = ssh.call_output(cmd, node=node)
    if cmdlines:
        cmdline = cmdlines.split('\n')[0].split('\0')
        for i, value in enumerate(cmdline):
            if value == '-c' and i < len(cmdline):
                return cmdline[i + 1]
    return '/etc/ceph/ceph.conf'


def add_rgw_frontends(conf):
    rgw_frontends_line = ("rgw_frontends = fastcgi socket_port=9000 "
                          "socket_host=127.0.0.1")
    conf = re.sub(r'\nkeyring = /etc/ceph/keyring.radosgw.gateway\n',
                  "\ng<1>{0}\n".format(rgw_frontends_line),
                  conf)
    return conf


def ceph_set_new_mons(seed_env, filename, conf_filename, db_path):
    nodes = list(env_util.get_controllers(seed_env))
    hostnames = map(short_hostname, node_util.get_hostnames(nodes))
    mgmt_ips = map(remove_mask, node_util.get_ips('management', nodes))

    with contextlib.closing(tarfile.open(filename)) as f:
        conf = f.extractfile(conf_filename).read()
        conf = replace_addresses(conf, hostnames, mgmt_ips)
        conf = add_rgw_frontends(conf)

    fsid = get_fsid(conf)
    monmaptool_cmd = ['monmaptool', '--fsid', fsid, '--clobber', '--create']
    for node_hostname, node_ip in itertools.izip(hostnames, mgmt_ips):
        monmaptool_cmd += ['--add', node_hostname, node_ip]

    for node, node_hostname in itertools.izip(nodes, hostnames):
        node_db_path = "/var/lib/ceph/mon/ceph-{0}".format(node_hostname)
        node_conf = replace_host(conf, node_hostname)
        try:
            ssh.call(['stop', 'ceph-mon', "id={0}".format(node_hostname)],
                     node=node)
        except subprocess.CalledProcessError:
            pass
        ssh.call(['rm', '-rf', node_db_path], node=node)
        node_util.untar_files(filename, node)
        sftp = ssh.sftp(node)
        with sftp.open(conf_filename, 'w') as f:
            f.write(node_conf)
        ssh.call(['mv', db_path, node_db_path], node=node)

        sysvinit = os.path.join(node_db_path, 'sysvinit')
        try:
            sftp.remove(sysvinit)
        except IOError:
            pass
        upstart = os.path.join(node_db_path, 'upstart')
        sftp.open(upstart, 'w').close()

        with ssh.tempdir(node) as tempdir:
            monmap_filename = os.path.join(tempdir, 'monmap')
            ssh.call(monmaptool_cmd + [monmap_filename], node=node)
            ssh.call(['ceph-mon', '-i', node_hostname, '--inject-monmap',
                      monmap_filename], node=node)

    for node, node_hostname in itertools.izip(nodes, hostnames):
        ssh.call(['start', 'ceph-mon', "id={0}".format(node_hostname)],
                 node=node)
    import_bootstrap_osd(nodes[0])


def extract_mon_conf_files(orig_env, tar_filename):
    controller = env_util.get_one_controller(orig_env)
    conf_filename = get_ceph_conf_filename(controller)
    conf_dir = os.path.dirname(conf_filename)
    hostname = short_hostname(
        node_util.get_hostname_remotely(controller))
    db_path = "/var/lib/ceph/mon/ceph-{0}".format(hostname)
    node_util.tar_files(tar_filename, controller, conf_dir, db_path)
    return conf_filename, db_path


def upgrade_ceph(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)

    tar_filename = os.path.join(magic_consts.FUEL_CACHE,
                                "env-{0}-ceph.conf.tar.gz".format(orig_id))
    conf_filename, db_path = extract_mon_conf_files(orig_env, tar_filename)
    ceph_set_new_mons(seed_env, tar_filename, conf_filename, db_path)


class UpgradeCephCommand(cmd.Command):
    """update Ceph cluster configuration."""

    def get_parser(self, prog_name):
        parser = super(UpgradeCephCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        return parser

    def take_action(self, parsed_args):
        upgrade_ceph(parsed_args.orig_id, parsed_args.seed_id)
