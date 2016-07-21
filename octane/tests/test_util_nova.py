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

from octane.util import nova


@pytest.mark.parametrize("cmd", [["my", "cmd"]])
@pytest.mark.parametrize("call_output", [True, False])
def test_nova_runner_call(mocker, cmd, call_output):
    env = mock.Mock()
    env.get_attributes.return_value = {"editable": {}}
    node = mock.Mock(data={"id": 1, "ip": "1.2.3.4"}, env=env)
    if call_output:
        ssh_call_mock = mocker.patch("octane.util.ssh.call_output")
    else:
        ssh_call_mock = mocker.patch("octane.util.ssh.call")
    nova.run_nova_cmd(cmd, node, call_output)
    ssh_call_mock.assert_called_once_with(
        ['sh', '-c', '. /root/openrc; ' + ' '.join(cmd)], node=node)
