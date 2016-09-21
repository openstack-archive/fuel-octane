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

import mock
import pytest

from octane.util import cinder

CINDER_OUTPUT_FULL = """
+------------------+-------------------------+---------+-------+
|      Binary      |           Host          |  Status | State |
+------------------+-------------------------+---------+-------+
|  cinder-backup   |       rbd:volumes       | enabled |  down |
| cinder-scheduler |       rbd:volumes       | enabled |  down |
|  cinder-volume   |       rbd:volumes       | enabled |  down |
|  cinder-volume   | rbd:volumes@RBD-backend | enabled |   up  |
+------------------+-------------------------+---------+-------+
"""
CINDER_OUTPUT_SHORT = """
+------------------+-------------------------+---------+-------+
|      Binary      |           Host          |  Status | State |
+------------------+-------------------------+---------+-------+
|  cinder-volume   | rbd:volumes@RBD-backend | enabled |   up  |
+------------------+-------------------------+---------+-------+
"""


@pytest.mark.parametrize(("output", "cmds"), [
    (CINDER_OUTPUT_FULL, [
        ["cinder-manage", "service", "remove", "cinder-backup", "rbd:volumes"],
        ["cinder-manage", "service", "remove", "cinder-scheduler",
         "rbd:volumes"],
        ["cinder-manage", "service", "remove", "cinder-volume", "rbd:volumes"],
    ]),
    (CINDER_OUTPUT_SHORT, []),
])
def test_remove_legacy_services_functional(mocker, output, cmds):
    controller = mock.Mock()
    mocker.patch("octane.util.node.run_with_openrc", return_value=output)
    mock_ssh = mocker.patch("octane.util.ssh.call")
    cinder.remove_legacy_services(controller)
    assert mock_ssh.call_args_list == [
        mock.call(cmd, node=controller) for cmd in cmds
    ]
