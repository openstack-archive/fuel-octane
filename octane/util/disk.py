# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os.path
import subprocess

from octane import magic_consts
from octane.util import ssh
from octane.util import subprocess


class NoDisksInfoError(Exception):
    message = "No disks info was found for node {0}"

    def __init__(self, node_id):
        super(NoDisksInfoError, self).__init__(self.message.format(node_id))


def get_node_disks(node):
    return node.get_attribute('disks')


def parse_last_partition_end(out):
    part_line = next(line for line in reversed(out.splitlines()) if line)
    # Example of part_line variable
    #  ID START   END     SIZE    TYPE
    # "7  32044MB 53263MB 21219MB primary"
    return int(part_line.split()[2][:-2])


# size in MB
def create_partition(disk_name, size, node):
    out = ssh.call_output(
        ['parted', '/dev/%s' % disk_name, 'unit', 'MB', 'print'], node=node)
    start = parse_last_partition_end(out) + 1
    end = start + size
    ssh.call(['parted', '/dev/%s' % disk_name, 'unit', 'MB', 'mkpart',
              'custom', 'ext4', str(start), str(end)],
             node=node)


def update_node_partition_info(node_id):
    fname = 'update_node_partition_info.py'
    command = ['python', os.path.join(magic_consts.CWD,
                                      'patches/{0}'.format(fname)), str(node_id)]
    subprocess.call(command)


def create_configdrive_partition(node):
    disks = get_node_disks(node)
    if not disks:
        raise NoDisksInfoError(node.data['id'])
    create_partition(disks[0]['name'],
                     magic_consts.CONFIGDRIVE_PART_SIZE,
                     node)
