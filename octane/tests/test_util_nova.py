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
@pytest.mark.parametrize("state", ["ACTIVE", "MIGRATING", None])
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
    assert exists == nova.do_nova_instances_exist(controller, node_fqdn, state)
    if state:
        nova_run_mock.assert_called_once_with([
            "nova", "list", "--host", node_fqdn,
            "--limit", "1", "--minimal", "--status", state], controller)
    else:
        nova_run_mock.assert_called_once_with([
            "nova", "list", "--host", node_fqdn,
            "--limit", "1", "--minimal"], controller)


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
        """
        +------+-------------+
        | ID   | Name        |
        +------+-------------+
        | id_1 | test_name_1 |
        | id_2 | test_name_2 |
        +------+-------------+
        """,
        [
            {
                "ID": "id_1",
                "Name": "test_name_1",
            },
            {
                "ID": "id_2",
                "Name": "test_name_2",
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
        "octane.util.nova.do_nova_instances_exist",
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


@pytest.mark.parametrize("cmd_output,enabled,disabled", [
    (
        """
            +----+--------+----------+
            | Id | Host   | Status   |
            +----+--------+----------+
            |  1 | node-1 | enabled  |
            |  2 | node-2 | enabled  |
            |  3 | node-3 | disabled |
            +----+--------+----------+
        """,
        ["node-1", "node-2"],
        ["node-3"]
    ),
])
def test_get_compute_lists(mocker, cmd_output, enabled, disabled):
    controller = mock.Mock()
    run_nova_cmd = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_output)

    assert (enabled, disabled) == nova.get_compute_lists(controller)
    run_nova_cmd.assert_called_once_with(
        ["nova", "service-list", "--binary", "nova-compute"], controller)


@pytest.mark.parametrize("cmd_out,result", [(
    "+--------------------------------------+\n"
    "| ID                                   |\n"
    "+--------------------------------------+\n"
    "| d5c35583-f498-4841-a032-069ec066d2d5 |\n"
    "| 8d274e6b-91db-4d76-a5e8-13a23c3335c9 |\n"
    "| 093c55f2-4a30-4a74-95ea-d7c39fcb4e3a |\n"
    "+--------------------------------------+\n",
    [
        "d5c35583-f498-4841-a032-069ec066d2d5",
        "8d274e6b-91db-4d76-a5e8-13a23c3335c9",
        "093c55f2-4a30-4a74-95ea-d7c39fcb4e3a",
    ]),
])
@pytest.mark.parametrize("node_fqdn", ["node_fqdn"])
def test_get_active_instances(mocker, cmd_out, result, node_fqdn):
    controller = mock.Mock()
    nova_mock = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_out)
    assert result == nova.get_active_instances(controller, node_fqdn)
    nova_mock.assert_called_once_with([
        "nova", "list",
        "--host", node_fqdn,
        "--limit", "-1",
        "--status", "ACTIVE",
        "--minimal"],
        controller)


@pytest.mark.parametrize(("levels", "version", "result", "error"), [
    ({"9.1": "liberty"}, "9.1", "liberty", False),
    ({"9.1": "liberty", "8.0": "kilo"}, "8.0", "kilo", False),
    ({}, "9.1", None, True),
])
def test_get_levels(mocker, levels, version, result, error):
    if error:
        msg = ("Could not find suitable upgrade_levels for the "
               "{version} release.".format(version=version))
        with pytest.raises(KeyError, message=msg):
            nova.get_levels(levels, version)
    else:
        assert nova.get_levels(levels, version) == result


@pytest.mark.parametrize(("func", "version", "result", "error"), [
    (nova.get_upgrade_levels, "9.1", "liberty", False),
    (nova.get_upgrade_levels, "8.0", "kilo", False),
    (nova.get_upgrade_levels, "9.x", None, True),
    (nova.get_upgrade_levels, "3.0", None, True),
    (nova.get_preupgrade_levels, "7.0", "liberty", False),
    (nova.get_preupgrade_levels, "9.x", None, True),
    (nova.get_preupgrade_levels, "3.0", None, True),
])
def test_get_levels_functional(mocker, func, version, result, error):
    if error:
        msg = ("Could not find suitable upgrade_levels for the "
               "{version} release.".format(version=version))
        with pytest.raises(KeyError, message=msg):
            func(version)
    else:
        assert func(version) == result
