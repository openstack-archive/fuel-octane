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
    get_env_mock = mocker.patch(
        "fuelclient.objects.Environment", return_value=env)
    nodes = [mock.MagicMock() for _ in range(node_count)]
    get_nodes_mock = mocker.patch(
        "octane.util.env.get_nodes", return_value=nodes)
    remove_compute_mock = mocker.patch(
        "octane.util.node.remove_compute_upgrade_levels")
    restart_service_mock = mocker.patch(
        "octane.util.node.restart_nova_services")
    cleanup.cleanup_environment(env_id)
    for node in nodes:
        remove_compute_mock.assert_any_call(node)
        restart_service_mock.assert_any_call(node)
    get_nodes_mock.assert_called_once_with(env, ["controller", "compute"])
    get_env_mock.assert_called_once_with(env_id)
