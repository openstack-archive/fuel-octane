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
import json

from octane.util import sql
from octane.util import ssh


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
    try:
        node_volumes_id, volumes_str = sql.run_psql_in_container(
            "select id, volumes from volume_manager_node_volumes "
            "where node_id={0}".format(node_id),
            "nailgun"
        )[0].split("|")
    except IndexError:
        raise Exception(
            "No volumes info was found for node {0}".format(node_id)
        )
    volumes = json.loads(volumes_str)
    try:
        os_data = next(disk for disk in volumes if disk.get("id") == "os")
    except StopIteration:
        return
    editable_volumes = [disk for disk in volumes if disk.get('id') != 'os']
    for disk in editable_volumes:
        disk_volumes, disk['volumes'] = disk['volumes'], []
        for volume in disk_volumes:
            if volume['type'] == 'pv' and \
                    volume['vg'] == 'os' and \
                    volume['size'] > 0:
                disk['volumes'].extend([
                    {
                        'name': v['name'],
                        'size': v['size'],
                        'type': 'partition',
                        'mount': v['mount'],
                        'file_system': v['file_system'],
                    }
                    for v in os_data['volumes']
                ])
                continue
            if volume['type'] == 'lvm_meta_pool' or volume['type'] == 'boot':
                volume['size'] = 0
            disk['volumes'].append(volume)
    sql.run_psql_in_container(
        "update volume_manager_node_volumes set volumes='{0}' "
        "where id={1}".format(json.dumps(volumes), node_volumes_id),
        "nailgun"
    )
