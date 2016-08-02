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


@pytest.mark.parametrize("cmd_output,enabled,disabled", [
    (
        "node-10|enabled\nnode-5|disabled\nnode-6|enabled\n",
        ["node-10", "node-6"],
        ["node-5"]
    ),
    (
        " node-10|enabled \n node-15|disabled \n node-6|enabled \n",
        ["node-10", "node-6"],
        ["node-15"]
    ),
])
def test_get_compute_lists(mocker, cmd_output, enabled, disabled):
    controller = mock.Mock()
    run_nova_cmd = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_output)

    assert (enabled, disabled) == compute.ComputeUpgrade._get_compute_lists(
        controller)
    run_nova_cmd.assert_called_once_with(
        ["nova", "service-list", "|",
         "awk", "'/nova-compute/ {print $6\"|\"$10}'"],
        controller,
        True
    )


@pytest.mark.parametrize("enabled", [["node-enabled-1", "node-enabled-2"],
                                     ["node-enabled-1"]])
@pytest.mark.parametrize("disabled", [["node-disabled-1", "node-disabled-2"],
                                      ["node-disabled-1"]])
@pytest.mark.parametrize("node_fqdn", ["node-disabled-1", "node-enabled-1"])
@pytest.mark.parametrize("nodes_in_error_state", [True, False])
@pytest.mark.parametrize("fuel_version", ["7.0", "8.0"])
def test_evacuate_host(
        mocker, enabled, disabled, node_fqdn, nodes_in_error_state, fuel_version):
    env = mock.Mock()
    controller = mock.Mock()
    node = mock.Mock()
    node.env = env
    node.env.data = {"fuel_version": fuel_version}

    mock_get_compute_list = mocker.patch.object(
        compute.ComputeUpgrade, "_get_compute_lists",
        return_value=(enabled, disabled))

    mock_get_one_controller = mocker.patch(
        "octane.util.env.get_one_controller", return_value=controller)

    run_nova_cmd = mocker.patch("octane.util.nova.run_nova_cmd")
    get_node_fqdn_mock = mocker.patch("octane.util.node.get_nova_node_handle",
                                      return_value=node_fqdn)
    mock_is_nova_state = mocker.patch.object(
        compute.ComputeUpgrade,
        "_is_nova_instances_exists_in_state",
        return_value=nodes_in_error_state)

    mock_waiting = mocker.patch.object(
        compute.ComputeUpgrade, "_waiting_for_state_completed")

    handler = compute.ComputeUpgrade(node, env, False, False)
    if [node_fqdn] == enabled:
        with pytest.raises(Exception):
            handler.evacuate_host()
        error = True
    elif nodes_in_error_state:
        with pytest.raises(Exception):
            handler.evacuate_host()
        error = True
    else:
        handler.evacuate_host()
        error = False
    nova_calls = []
    if node_fqdn not in disabled:
        nova_calls.append(mock.call(
            ["nova", "service-disable", node_fqdn, "nova-compute"],
            controller, False))
    nova_calls.append(mock.call(
        ['nova', 'host-evacuate-live', node_fqdn], controller, False))
    if error:
        assert not run_nova_cmd.called
        assert not mock_waiting.called
    else:
        assert run_nova_cmd.call_args_list == nova_calls
        mock_waiting.assert_called_once_with(
            controller, node_fqdn, "MIGRATING",
            compute.TimeoutHostEvacuationException)
    if [node_fqdn] == enabled:
        assert not mock_is_nova_state.called
    else:
        mock_is_nova_state.assert_called_once_with(
            controller, node_fqdn, "ERROR")
    get_node_fqdn_mock.assert_called_once_with(node)
    mock_get_compute_list.assert_called_once_with(controller)
    mock_get_one_controller.assert_called_once_with(env)


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
