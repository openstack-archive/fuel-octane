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


@pytest.mark.parametrize("node_fqdn", ["fqdn"])
@pytest.mark.parametrize("state", ["ACTIVE", "MIGRATING"])
@pytest.mark.parametrize("cmd_output,exists", [
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        | 85cfb077-3397-405e-ae61-dfce35d3073a | test_boot_volume_2 |
        +--------------------------------------+--------------------+""",
        True,
    ),
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        | 85cfb077-3397-405e-ae61-dfce35d3073a | test_boot_volume_2 |
        +--------------------------------------+--------------------+\n\n
        """,
        True,
    ),
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        +--------------------------------------+--------------------+\n\n
        """,
        False,
    ),
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        +--------------------------------------+--------------------+
        """,
        False,
    ),
]
)
def test_is_there_nova_instances_exists_in_status(
        mocker, node_fqdn, state, cmd_output, exists):
    controller = mock.Mock()
    nova_run_mock = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_output)
    assert exists == nova.do_nova_instances_exist_in_status(
        controller, node_fqdn, state)
    nova_run_mock.assert_called_once_with([
        "nova", "list", "--host", node_fqdn,
        "--status", state, "--limit", "1", "--minimal"], controller)


@pytest.mark.parametrize("cmd_output, expected_result", [
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        | 85cfb077-3397-405e-ae61-dfce35d3073a | test_boot_volume_2 |
        +--------------------------------------+--------------------+""",
        [
            {
                "ID": "85cfb077-3397-405e-ae61-dfce35d3073a",
                "Name": "test_boot_volume_2",
            }
        ]
    ),
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        +--------------------------------------+--------------------+""",
        []
    ),
])
def test_nova_stdout_parser(cmd_output, expected_result):
    assert expected_result == nova.nova_stdout_parser(cmd_output)


@pytest.mark.parametrize("node_fqdn", ["fqdn"])
@pytest.mark.parametrize("state", ["ACTIVE", "MIGRATING"])
@pytest.mark.parametrize("delay", [100])
@pytest.mark.parametrize("attempts,result_attempt",
                         [(10, 10), (100, 1), (10, 11)])
def test_waiting_for_status_completed(
        mocker, node, node_fqdn, state, delay, attempts, result_attempt):
    controller = mock.Mock()
    timeout_calls = []
    check_instances_exist_side_effects = []
    check_instances_exist_calls = []
    for idx in range(1, min(attempts, result_attempt) + 1):
        if idx < result_attempt:
            timeout_calls.append(mock.call(delay))
        check_instances_exist_side_effects.append(idx != result_attempt)
        check_instances_exist_calls.append(
            mock.call(controller, node_fqdn, state))
    mock_patch_is_nova_state = mocker.patch(
        "octane.util.nova.do_nova_instances_exist_in_status",
        side_effect=check_instances_exist_side_effects)
    mock_sleep = mocker.patch("time.sleep")

    if result_attempt > attempts:
        with pytest.raises(nova.WaiterException):
            nova.waiting_for_status_completed(
                controller, node_fqdn, state, attempts, delay)
    else:
        nova.waiting_for_status_completed(
            controller, node_fqdn, state, attempts, delay)

    assert timeout_calls == mock_sleep.call_args_list
    assert check_instances_exist_calls == \
        mock_patch_is_nova_state.call_args_list
