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

import os

from octane.util import disk as disk_util


def test_create_partition(mocker, mock_ssh_call, mock_ssh_call_output, node):
    test_size = 1
    test_disk = 'disk'
    mock_node = node
    mock_part_end = mocker.patch("octane.util.disk.parse_last_partition_end")
    mock_part_end.return_value = 1

    disk_util.create_partition(test_disk, test_size, mock_node)
    mock_ssh_call_output.assert_called_once_with(
        ['parted', '/dev/%s' % test_disk, 'unit', 'MB', 'print'], node=node)
    mock_ssh_call.assert_called_once_with(
        ['parted', '/dev/%s' % test_disk, 'unit', 'MB', 'mkpart',
         'custom', 'ext4', str(2), str(3)], node=node)


def test_update_partition_info(mocker, node):
    test_node_id = 1
    container = 'nailgun'
    mock_run_in_container = mocker.patch(
        "octane.util.docker.run_in_container")
    expected_command = [
        'python',
        os.path.join('/tmp', 'update_node_partition_info.py'),
        str(test_node_id),
    ]
    disk_util.update_node_partition_info(test_node_id)
    mock_run_in_container.assert_called_once_with(container, expected_command)
