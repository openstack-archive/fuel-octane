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

    mock_get_compute_list = mocker.patch("octane.util.nova.get_compute_lists",
                                         return_value=(enabled, disabled))

    mock_get_one_controller = mocker.patch(
        "octane.util.env.get_one_controller", return_value=controller)

    run_nova_cmd = mocker.patch("octane.util.nova.run_nova_cmd")
    get_node_fqdn_mock = mocker.patch("octane.util.node.get_nova_node_handle",
                                      return_value=node_fqdn)
    mock_is_nova_state = mocker.patch(
        "octane.util.nova.do_nova_instances_exist",
        return_value=nodes_in_error_state)

    get_instances_mock = mocker.patch(
        "octane.util.nova.get_active_instances", return_value=instances)

    mock_waiting = mocker.patch(
        "octane.util.nova.waiting_for_status_completed")

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
        waiting_calls = [mock.call(controller, node_fqdn, "MIGRATING")
                         for i in instances]
        assert waiting_calls == mock_waiting.call_args_list
    if [node_fqdn] == enabled:
        assert not mock_is_nova_state.called
    else:
        if error:
            mock_is_nova_state.assert_called_once_with(
                controller, node_fqdn, "ERROR")
        else:
            assert [
                mock.call(controller, node_fqdn, "ERROR"),
                mock.call(controller, node_fqdn),
            ] == mock_is_nova_state.call_args_list
    get_node_fqdn_mock.assert_called_once_with(node)
    mock_get_compute_list.assert_called_once_with(controller)
    mock_get_one_controller.assert_called_once_with(env)


@pytest.mark.parametrize("fuel_version", ["7.0", "8.0"])
@pytest.mark.parametrize("password", ["password"])
@pytest.mark.parametrize("node_fqdn", ["node-compute"])
@pytest.mark.parametrize("cmd_output, instances", [(
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
    mock_waiting = mocker.patch(
        "octane.util.nova.waiting_for_status_completed")
    mock_is_nova_state = mocker.patch(
        "octane.util.nova.do_nova_instances_exist",
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
            "--minimal"],
            controller))
        for instance in instances:
            nova_run_calls.append(mock.call(
                ["nova", "stop", instance], controller, output=False))
        assert nova_run_calls == mock_nova_run.call_args_list
        mock_waiting.assert_called_once_with(controller, node_fqdn, "ACTIVE")
    mock_get_one_controller.assert_called_once_with(env)
    mock_get_node_fqdn.assert_called_once_with(node)
    mock_is_nova_state.assert_called_once_with(controller, node_fqdn, "ERROR")
