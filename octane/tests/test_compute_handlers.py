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

from octane.handlers.upgrade import compute

import mock
import pytest


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
def test_is_nova_instances_exists_in_state(
        mocker, node_fqdn, state, cmd_output, exists):
    controller = mock.Mock()
    nova_run_mock = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_output)
    assert exists == compute.ComputeUpgrade._is_nova_instances_exists_in_state(
        controller, node_fqdn, state)
    nova_run_mock.assert_called_once_with([
        "nova", "list", "--host", node_fqdn,
        "--status", state, "--limit", "1", "--minimal"], controller)


@pytest.mark.parametrize("node_fqdn", ["fqdn"])
@pytest.mark.parametrize("state", ["ACTIVE", "MIGRATING"])
@pytest.mark.parametrize("delay", [100])
@pytest.mark.parametrize("attempts,result_attempt",
                         [(10, 10), (100, 1), (10, 11)])
def test_waiting_for_state_completed(
        mocker, node, node_fqdn, state, delay, attempts, result_attempt):

    class TestException(compute.TimeoutException):
        message = "{hostname} {attempts}"

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
    mock_patch_is_nova_state = mocker.patch.object(
        compute.ComputeUpgrade,
        "_is_nova_instances_exists_in_state",
        side_effect=check_instances_exist_side_effects)
    mock_sleep = mocker.patch("time.sleep")

    if result_attempt > attempts:
        with pytest.raises(TestException):
            compute.ComputeUpgrade._waiting_for_state_completed(
                controller, node_fqdn, state, TestException, attempts, delay)
    else:
        compute.ComputeUpgrade._waiting_for_state_completed(
            controller, node_fqdn, state, TestException, attempts, delay)

    assert timeout_calls == mock_sleep.call_args_list
    assert check_instances_exist_calls == \
        mock_patch_is_nova_state.call_args_list


@pytest.mark.parametrize("password", ["password"])
@pytest.mark.parametrize("fqdn", ["fqdn"])
@pytest.mark.parametrize("node_id", [1])
@pytest.mark.parametrize("instances_cmd_out,expected_instances", [
    ("in1\nin2\nin3\n", ["in1", "in2", "in3"]),
    (" in1 \n in2 \n in3 \n", ["in1", "in2", "in3"]),
])
@pytest.mark.parametrize("fuel_version,is_fqdn_call", [
    ("6.0", False), ("6.1", True), ("7.0", True), ("8.0", True)])
def test_shutoff_vm(
        mocker, password, instances_cmd_out, expected_instances,
        fqdn, is_fqdn_call, node_id, fuel_version):
    mocker.patch.object(
        compute.ComputeUpgrade, "_waiting_for_state_completed")
    env_mock = mock.Mock()
    node = mock.Mock()
    node.env.data = {"fuel_version": fuel_version}
    ssh_call_output_mock = mocker.patch(
        "octane.util.ssh.call_output", return_value=instances_cmd_out)
    ssh_call_mock = mocker.patch("octane.util.ssh.call")
    node.data = {'fqdn': fqdn, 'id': node_id}
    controller = mock.Mock()

    mock_get_pswd = mocker.patch(
        "octane.util.env.get_admin_password", return_value=password)
    mock_get_controller = mocker.patch(
        "octane.util.env.get_one_controller", return_value=controller)

    handler = compute.ComputeUpgrade(node, env_mock, False, False)

    handler.shutoff_vms()
    hostname = fqdn if is_fqdn_call else "node-{}".format(node_id)
    ssh_call_output_mock.assert_called_once_with(
        [
            "sh", "-c",
            ". /root/openrc; "
            "nova --os-password {0} list --host {1} --limit -1".format(
                password, hostname) +
            " | awk -F\| '$4~/ACTIVE/{print($2)}'"
        ],
        node=controller
    )
    assert [mock.call(["sh", "-c", ". /root/openrc; nova stop {0}".format(e)],
                      node=controller)
            for e in expected_instances] == ssh_call_mock.call_args_list
    mock_get_pswd.assert_called_once_with(env_mock)
    mock_get_controller.assert_called_once_with(env_mock)
