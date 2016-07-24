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
import os
import re
import subprocess
import tarfile

from distutils import version

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
    if re.search(r"\nrgw_frontends", conf):
        return conf
    conf = re.sub(r'\n\[client.radosgw.gateway\]\n',
                  "\g<0>{0}\n".format(rgw_frontends_line),
                  conf)
    return conf


def change_fsid(conf_file_path, node, fsid):
    with ssh.update_file(ssh.sftp(node), conf_file_path) as (old, new):
        for line in old:
            if line.startswith("fsid"):
                line = u"fsid = {0}\n".format(fsid)
            new.write(line)


def _activate_upstart_insed_sysvint(node, db_path, node_db_path):
    sftp = ssh.sftp(node)

    ssh.call(['mv', db_path, node_db_path], node=node)

    sysvinit = os.path.join(node_db_path, 'sysvinit')
    try:
        sftp.remove(sysvinit)
    except IOError:
        pass
    upstart = os.path.join(node_db_path, 'upstart')
    sftp.open(upstart, 'w').close()


def ceph_set_new_mons(orig_env, seed_env, filename, conf_filename, db_path):
    nodes = list(env_util.get_controllers(seed_env))

    with contextlib.closing(tarfile.open(filename)) as f:
        conf = f.extractfile(conf_filename).read()

    fsid = get_fsid(conf)

    for node in nodes:
        node_hostname = short_hostname(node.data['fqdn'])
        node_db_path = "/var/lib/ceph/mon/ceph-{0}".format(node_hostname)
        try:
            ssh.call(['stop', 'ceph-mon', "id={0}".format(node_hostname)],
                     node=node)
        except subprocess.CalledProcessError:
            pass
        with ssh.tempdir(node) as tempdir:
            # save current seed conf and monmap in tmp dir
            monmap_filename = os.path.join(tempdir, 'monmap')
            ssh.call(["ceph-mon", "-i", node_hostname,
                     "--extract-monmap", monmap_filename], node=node)
            seed_conf_path = os.path.join(tempdir, "ceph.conf")
            ssh.call(['cp', conf_filename, seed_conf_path], node=node)

            ssh.call(['rm', '-rf', node_db_path], node=node)
            node_util.untar_files(filename, node)

            # return seed ceph confs
            ssh.call(['cp', seed_conf_path, conf_filename], node=node)
            # change fsid for orig fsid value
            change_fsid(conf_filename, node, fsid)
            # change fsid value in monmap
            ssh.call(["monmaptool", "--fsid", fsid,
                      "--clobber", monmap_filename], node=node)
            if version.StrictVersion(orig_env.data["fuel_version"]) < \
                    version.StrictVersion(magic_consts.CEPH_UPSTART_VERSION):
                _activate_upstart_insed_sysvint(node, db_path, node_db_path)
            # return old monmap value
            ssh.call(['ceph-mon', '-i', node_hostname,
                      '--inject-monmap', monmap_filename], node=node)
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
    ceph_set_new_mons(orig_env, seed_env, tar_filename, conf_filename, db_path)


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
