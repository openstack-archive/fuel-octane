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

import pytest

from octane.util import ceph


@pytest.mark.parametrize("cmd_output,conf_file", [
    (
        "/usr/bin/ceph-mon\0--cluster=ceph\0-i\0node-4\0-f",
        "/etc/ceph/ceph.conf"
    ),
    ("", "/etc/ceph/ceph.conf"),
    (
        "/usr/bin/ceph-mon\0--cluster=ceph\0-i\0node-4\0-f\0-c\0new_conf_path",
        "new_conf_path"
    ),
])
def test_get_ceph_conf_filename(mocker, node, cmd_output, conf_file):
    cmd = [
        'bash', '-c',
        'pgrep ceph-mon | xargs -I{} cat /proc/{}/cmdline',
    ]
    mock_ssh = mocker.patch(
        "octane.util.ssh.call_output", return_value=cmd_output)
    assert conf_file == ceph.get_ceph_conf_filename(node)
    mock_ssh.assert_called_once_with(cmd, node=node)
