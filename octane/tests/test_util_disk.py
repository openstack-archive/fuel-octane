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

import json
from octane.util import disk

NODE_VOLUMES = [
    {
        "name": "vda",
        "extra": ["disk/by-id/virtio-2a1c4ae380c04f6980f9"],
        "free_space": 50572,
        "volumes": [
            {"type": "boot", "size": 300},
            {
                "mount": "/boot",
                "type": "raid",
                "file_system": "ext2",
                "name": "Boot",
                "size": 200
            },
            {
                "type": "lvm_meta_pool",
                "size": 0
            },
            {
                "vg": "os",
                "type": "pv",
                "lvm_meta_size": 64,
                "size": 19472
            },
            {
                "partition_guid": "45b0969e-9b03-4f30-b4c6-b4b80ceff106",
                "name": "cephjournal",
                "mount": "none",
                "disk_label": None,
                "type": "partition",
                "file_system": "none",
                "size": 0
            },
            {
                "partition_guid": "4fbd7e29-9d25-41b8-afd0-062c0ceff05d",
                "name": "ceph",
                "mount": "none",
                "disk_label": None,
                "type": "partition",
                "file_system": "none",
                "size": 0
            },
            {
                "vg": "vm",
                "type": "pv",
                "lvm_meta_size": 64,
                "size": 31228
            }
        ],
        "type": "disk",
        "id": "disk/by-path/pci-0000:00:09.0-virtio-pci-virtio0",
        "size": 51200
    },
    {
        "_allocate_size": "min",
        "label": "Base System",
        "min_size": 19408,
        "volumes": [
            {
                "mount": "/",
                "type": "lv",
                "name": "root",
                "file_system": "ext4",
                "size": 15360
            },
            {
                "mount": "swap",
                "type": "lv",
                "name": "swap",
                "file_system": "swap",
                "size": 4048
            }
        ],
        "type": "vg",
        "id": "os"
    }
]

EXPECTED_VOLUMES = [
    {
        'name': 'vda',
        'extra': ['disk/by-id/virtio-2a1c4ae380c04f6980f9'],
        'free_space': 50572,
        'volumes': [
            {'type': 'boot', 'size': 0},
            {
                'mount': '/boot',
                'type': 'raid',
                'file_system': 'ext2',
                'name': 'Boot',
                'size': 200
            },
            {'type': 'lvm_meta_pool', 'size': 0},
            {
                'mount': '/',
                'type': 'partition',
                'name': 'root',
                'file_system': 'ext4',
                'size': 15360
            },
            {
                'mount': 'swap',
                'type': 'partition',
                'name': 'swap',
                'file_system': 'swap',
                'size': 4048
            },
            {
                'partition_guid': '45b0969e-9b03-4f30-b4c6-b4b80ceff106',
                'name': 'cephjournal',
                'mount': 'none',
                'disk_label': None,
                'type': 'partition',
                'file_system': 'none',
                'size': 0
            },
            {
                'partition_guid': '4fbd7e29-9d25-41b8-afd0-062c0ceff05d',
                'name': 'ceph',
                'mount': 'none',
                'disk_label': None,
                'type': 'partition',
                'file_system': 'none',
                'size': 0
            },
            {
                'vg': 'vm',
                'type': 'pv',
                'lvm_meta_size': 64,
                'size': 31228
            }
        ],
        'type': 'disk',
        'id': 'disk/by-path/pci-0000:00:09.0-virtio-pci-virtio0',
        'size': 51200
    },
    {
        '_allocate_size': 'min',
        'label': 'Base System',
        'min_size': 19408,
        'volumes': [
            {
                'mount': '/',
                'type': 'lv',
                'name': 'root',
                'file_system': 'ext4',
                'size': 15360
            },
            {
                'mount': 'swap',
                'type': 'lv',
                'name': 'swap',
                'file_system': 'swap',
                'size': 4048
            }
        ],
        'type': 'vg',
        'id': 'os'
    }
]


def test_update_partition_info(mocker):
    volume_id = 1
    volume_value = json.dumps(NODE_VOLUMES)
    sql_mocker = mocker.patch(
        "octane.util.sql.run_psql_in_container",
        return_value=["{0}|{1}".format(volume_id, volume_value)])
    jsoned_value = "jsoned_value"
    json_mocker = mocker.patch("json.dumps", return_value=jsoned_value)
    disk.update_node_partition_info(volume_id)
    json_mocker.assert_called_with(EXPECTED_VOLUMES)
    sql_mocker.assert_called_with(
        "update volume_manager_node_volumes set volumes='{0}' "
        "where id={1}".format(jsoned_value, volume_id),
        "nailgun"
    )
