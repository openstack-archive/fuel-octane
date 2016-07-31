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
