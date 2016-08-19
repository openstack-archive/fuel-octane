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

from octane.commands import upgrade_controlplane


@pytest.mark.parametrize("ceph_osd_count", [0, 1, 10])
@pytest.mark.parametrize("compute_count", [0, 1, 10])
@pytest.mark.parametrize("ceph_conf", ["ceph_conf"])
@pytest.mark.parametrize("ceph_conf_file", ["ceph_conf_file"])
def test_upgrade_osd(
        mocker, ceph_osd_count, compute_count, ceph_conf, ceph_conf_file):
    orig_env = mock.Mock()
    seed_env = mock.Mock()
    ceph_nodes = [mock.MagicMock(data={'roles': ['ceph-osd']})
                  for n in range(ceph_osd_count)]
    compute_nodes = [mock.MagicMock(data={'roles': ['compute']})
                     for n in range(compute_count)]
    nodes = ceph_nodes + compute_nodes
    for node in nodes:
        node.__enter__.return_value = (None, node)
    get_nodes_mock = mocker.patch(
        "octane.util.env.get_nodes", return_value=nodes)
    controller = mock.Mock()
    get_controller_mock = mocker.patch(
        "octane.util.env.get_one_controller", return_value=controller)
    ssh_mock = mocker.patch("octane.util.ssh.call")
    ssh_mock_call_output = mocker.patch("octane.util.ssh.call_output",
                                        return_value=ceph_conf)
    sftp_mock = mocker.patch("octane.util.ssh.sftp", side_effect=lambda n: n)
    ssh_mock_update_file = mocker.patch("octane.util.ssh.update_file",
                                        side_effect=lambda x, c: x)
    get_ceph_conf_mock = mocker.patch(
        "octane.util.ceph.get_ceph_conf_filename", return_value=ceph_conf_file)
    upgrade_controlplane.upgrade_osd(orig_env, seed_env)
    get_nodes_mock.assert_called_once_with(orig_env, ['ceph-osd', 'compute'])
    if ceph_osd_count:
        ssh_calls = [
            mock.call(["ceph", "osd", "set", "noout"], node=ceph_nodes[0]),
            mock.call(["ceph", "osd", "set", "noout"], node=controller)
        ]

        for node in ceph_nodes:
            ssh_calls.append(mock.call(["restart", "ceph-osd-all"], node=node))
        ssh_calls.append(
            mock.call(["ceph", "osd", "unset", "noout"], node=ceph_nodes[0]))
        assert ssh_calls == ssh_mock.call_args_list
        ssh_mock_call_output.assert_called_once_with(
            ['cat', ceph_conf_file], node=controller)
        get_controller_mock.assert_called_once_with(seed_env)
        for node in (ceph_nodes + compute_nodes):
            node.write.assert_called_once_with(ceph_conf)
            ssh_mock_update_file.assert_any_call(node, ceph_conf_file)
            sftp_mock.assert_any_call(node)
        get_ceph_conf_mock.assert_called_once_with(controller)
    else:
        assert not ssh_mock.called
        assert not ssh_mock_call_output.called
        assert not get_controller_mock.called
        assert not get_ceph_conf_mock.called
