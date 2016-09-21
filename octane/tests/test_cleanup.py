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

from octane.commands import cleanup


@pytest.mark.parametrize("env_id", [1])
@pytest.mark.parametrize("node_count", [0, 1, 10])
def test_cleanup_env(mocker, env_id, node_count):
    env = mock.Mock()
    controller = mock.Mock()
    get_env_mock = mocker.patch(
        "fuelclient.objects.Environment", return_value=env)
    nodes = [mock.Mock() for idx in range(node_count)]
    get_controller = mocker.patch(
        "octane.util.env.get_one_controller", return_value=controller)
    clean_services_mock = mocker.patch(
        "octane.commands.cleanup.clean_services_for_node")
    get_nodes_mock = mocker.patch(
        "octane.util.env.get_nodes", return_value=nodes)
    remove_compute_mock = mocker.patch(
        "octane.util.node.remove_compute_upgrade_levels")
    restart_service_mock = mocker.patch(
        "octane.util.node.restart_nova_services")
    remove_cinder_mock = mocker.patch(
        "octane.util.cinder.remove_legacy_services")
    cleanup.cleanup_environment(env_id)
    for node in nodes:
        remove_compute_mock.assert_any_call(node)
        restart_service_mock.assert_any_call(node)
        clean_services_mock.assert_any_call(controller, node)
    assert len(nodes) == clean_services_mock.call_count
    get_nodes_mock.assert_called_once_with(env, ["controller", "compute"])
    get_env_mock.assert_called_once_with(env_id)
    get_controller.assert_called_once_with(env)
    remove_cinder_mock.assert_called_once_with(controller)


@pytest.mark.parametrize("hostname", ["test_hostname"])
@pytest.mark.parametrize("stdout,deleted_services", [(
    "   +----+\n"
    "   | Id |\n"
    "   +----+\n"
    "   | 1  |\n"
    "   | 2  |\n"
    "   | 3  |\n"
    "   +----+\n",
    ["1", "2", "3"]
)])
def test_clean_services_for_node(mocker, hostname, stdout, deleted_services):
    node = mock.MagicMock(data={"hostname": hostname})
    controller = mock.Mock()
    nova_run_mock = mocker.patch(
        "octane.util.node.run_with_openrc", return_value=stdout)
    cleanup.clean_services_for_node(controller, node)
    for service_id in deleted_services:
        nova_run_mock.assert_any_call(
            ["nova", "service-delete", service_id], controller, output=False)
    get_service_call = mock.call(
        ["nova", "service-list", "--host", hostname], controller)
    assert get_service_call == nova_run_mock.call_args_list[0]
