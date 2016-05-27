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
import pytest

from octane.util import disk as disk_util


@pytest.mark.parametrize("disk", ["sda", "sdb", "sdc"])
@pytest.mark.parametrize("size,last_part,end_part", [
    (10, 1024, 1035),
    (0, 10, 11),
])
def test_create_partition(mocker, mock_ssh_call, mock_ssh_call_output, node,
                          size, last_part, end_part, disk):
    mock_part_end = mocker.patch("octane.util.disk.parse_last_partition_end")
    mock_part_end.return_value = last_part

    disk_util.create_partition(disk, size, node)
    mock_ssh_call_output.assert_called_once_with(
        ['parted', '/dev/%s' % disk, 'unit', 'MB', 'print'], node=node)
    mock_ssh_call.assert_called_once_with(
        ['parted', '/dev/%s' % disk, 'unit', 'MB', 'mkpart',
         'custom', 'ext4', str(last_part + 1), str(end_part)], node=node)


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
