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

from oslo_log import log as logging

from octane.util import env as env_util
from octane.util import ssh

LOG = logging.getLogger(__name__)


def check_cluster(node):
    # From check_ceph_cluster
    res = ssh.call_output(['ceph', 'health'], node=node)
    LOG.debug('Got status: %s', res)
    if not res or 'HEALTH_OK' not in res:
        raise Exception("Ceph cluster is unhealthy: " + res)


def set_osd_noout(env):
    controller = env_util.get_one_controller(env)
    ssh.call(['ceph', 'osd', 'set', 'noout'], node=controller)


def unset_osd_noout(env):
    controller = env_util.get_one_controller(env)
    ssh.call(['ceph', 'osd', 'unset', 'noout'], node=controller)


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


def restart_radosgw(env):
    node = env_util.get_one_controller(env)
    ssh.call(["service", "radosgw", "restart"], node=node)
