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
def test_is_nova_instances_exists(
        mocker, node_fqdn, state, cmd_output, exists):
    controller = mock.Mock()
    nova_run_mock = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_output)
    assert exists == compute.ComputeUpgrade._is_nova_instances_exists(
        controller, node_fqdn, state)
    if state:
        nova_run_mock.assert_called_once_with([
            "nova", "list", "--host", node_fqdn,
            "--limit", "1", "--minimal", "--status", state], controller)
    else:
        nova_run_mock.assert_called_once_with([
            "nova", "list", "--host", node_fqdn,
            "--limit", "1", "--minimal"], controller)


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
        "_is_nova_instances_exists",
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
@pytest.mark.parametrize("instances", [["instance_1", "instance_2"]])
def test_evacuate_host(mocker, enabled, disabled, node_fqdn,
                       nodes_in_error_state, fuel_version, instances):
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
    get_instances_mock = mocker.patch.object(
        compute.ComputeUpgrade,
        "_get_active_instances",
        return_value=instances)
    get_node_fqdn_mock = mocker.patch("octane.util.node.get_nova_node_handle",
                                      return_value=node_fqdn)
    mock_is_nova_state = mocker.patch.object(
        compute.ComputeUpgrade,
        "_is_nova_instances_exists",
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
    for instance in instances:
        nova_calls.append(mock.call(
            ["nova", "live-migration", instance], controller, False))
    if error:
        assert not run_nova_cmd.called
        assert not mock_waiting.called
        assert not get_instances_mock.called
    else:
        assert run_nova_cmd.call_args_list == nova_calls
        get_instances_mock.assert_called_once_with(controller, node_fqdn)
        waiting_calls = [
            mock.call(controller, node_fqdn,
                      "MIGRATING", compute.TimeoutHostEvacuationException)
            for i in instances]
        assert waiting_calls == mock_waiting.call_args_list
    if [node_fqdn] == enabled:
        assert not mock_is_nova_state.called
    else:
        mock_is_nova_state.assert_any_call(controller, node_fqdn, "ERROR")
        if not error:
            mock_is_nova_state.assert_any_call(controller, node_fqdn)
        assert 1 + (not error) == mock_is_nova_state.call_count
    get_node_fqdn_mock.assert_called_once_with(node)
    mock_get_compute_list.assert_called_once_with(controller)
    mock_get_one_controller.assert_called_once_with(env)


@pytest.mark.parametrize("fuel_version", ["7.0", "8.0"])
@pytest.mark.parametrize("password", ["password"])
@pytest.mark.parametrize("node_fqdn", ["node-compute"])
@pytest.mark.parametrize("cmd_output, instances", [(
    "\n\n\n0389c396-c703-4a08-9da9-b2da7b6db2c0  \n"
    "265690ad-7e31-4fec-8f28-4f1edb0b1f09  \n"
    "85cfb077-3397-405e-ae61-dfce35d3073a  \n\n\n",
    [
        "0389c396-c703-4a08-9da9-b2da7b6db2c0",
        "265690ad-7e31-4fec-8f28-4f1edb0b1f09",
        "85cfb077-3397-405e-ae61-dfce35d3073a",
    ]),
])
@pytest.mark.parametrize("nodes_in_error_state", [True, False])
def test_shutoff_vms(
        mocker, fuel_version, password, node_fqdn, cmd_output,
        instances, nodes_in_error_state):
    env = mock.Mock()
    controller = mock.Mock()
    node = mock.Mock()
    node.env = env
    node.env.data = {"fuel_version": fuel_version}
    handler = compute.ComputeUpgrade(node, env, False, False)
    mock_get_one_controller = mocker.patch(
        "octane.util.env.get_one_controller", return_value=controller)
    mock_get_node_fqdn = mocker.patch(
        "octane.util.node.get_nova_node_handle", return_value=node_fqdn)
    mock_nova_run = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_output)
    mock_waiting = mocker.patch.object(
        compute.ComputeUpgrade, "_waiting_for_state_completed")
    mock_is_nova_state = mocker.patch.object(
        compute.ComputeUpgrade,
        "_is_nova_instances_exists",
        return_value=nodes_in_error_state)
    nova_run_calls = []
    if nodes_in_error_state:
        with pytest.raises(Exception):
            handler.shutoff_vms()
        assert not mock_nova_run.called
        assert not mock_waiting.called
    else:
        handler.shutoff_vms()
        nova_run_calls.append(mock.call([
            "nova", "list",
            "--host", node_fqdn,
            "--limit", "-1",
            "--status", "ACTIVE",
            "--minimal", "|",
            "awk 'NR>2 {print $2}'"],
            controller))
        for instance in instances:
            nova_run_calls.append(mock.call(
                ["nova", "stop", instance], controller, output=False))
        assert nova_run_calls == mock_nova_run.call_args_list
        mock_waiting.assert_called_once_with(
            controller, node_fqdn, "ACTIVE", compute.TimeoutStopVMException)
    mock_get_one_controller.assert_called_once_with(env)
    mock_get_node_fqdn.assert_called_once_with(node)
    mock_is_nova_state.assert_called_once_with(controller, node_fqdn, "ERROR")


@pytest.mark.parametrize("cmd_out,result", [(
    "\n\n\n0389c396-c703-4a08-9da9-b2da7b6db2c0  \n"
    "265690ad-7e31-4fec-8f28-4f1edb0b1f09  \n"
    "85cfb077-3397-405e-ae61-dfce35d3073a  \n\n\n",
    [
        "0389c396-c703-4a08-9da9-b2da7b6db2c0",
        "265690ad-7e31-4fec-8f28-4f1edb0b1f09",
        "85cfb077-3397-405e-ae61-dfce35d3073a",
    ]),
])
@pytest.mark.parametrize("node_fqdn", ["node_fqdn"])
def test_get_active_instances(mocker, cmd_out, result, node_fqdn):
    controller = mock.Mock()
    nova_mock = mocker.patch(
        "octane.util.nova.run_nova_cmd", return_value=cmd_out)
    assert result == compute.ComputeUpgrade._get_active_instances(
        controller, node_fqdn)
    nova_mock.assert_called_once_with([
        "nova", "list",
        "--host", node_fqdn,
        "--limit", "-1",
        "--status", "ACTIVE",
        "--minimal", "|",
        "awk 'NR>2 {print $2}'"],
        controller)
