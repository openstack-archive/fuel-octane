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

import contextlib
import mock
import pytest

from octane.commands import osd_upgrade
from octane import magic_consts
from octane.util import ssh


@pytest.mark.parametrize("env_id", [None, 1, 2])
@pytest.mark.parametrize("admin_pswd", [None, "pswd"])
def test_osd_cmd_upgrade(mocker, octane_app, env_id, admin_pswd):
    upgrade_osd_mock = mocker.patch("octane.commands.osd_upgrade.upgrade_osd")
    params = ["upgrade-osd"]
    if admin_pswd:
        params += ["--admin-password", admin_pswd]
    if env_id:
        params += [str(env_id)]
    if env_id and admin_pswd:
        octane_app.run(params)
        upgrade_osd_mock.assert_called_once_with(env_id, "admin", admin_pswd)
        return
    with pytest.raises(AssertionError):
        octane_app.run(params)
    assert not upgrade_osd_mock.called


@pytest.mark.parametrize("node_roles, exception_node", [
    ([('ceph-osd', ), ] * 10, None),
    ([('ceph-osd', 'compute'), ] * 10, None),
    ([('ceph-osd', ), ('compute', )] * 10, None),
    ([('ceph-osd', ), ('compute', ), ('controller', )] * 10, None),
    ([], None),
    ([('compute', ), ] * 10, None),
    ([('ceph-osd', ), ] * 10, 0),
    ([('ceph-osd', ), ('compute', )] * 10, 3),
    ([('ceph-osd', ), ('compute', )] * 10, 7),
    ([('ceph-osd', ), ('compute', )] * 10, 9),
])
@pytest.mark.parametrize("user", ["usr", "admin"])
@pytest.mark.parametrize("password", ["admin", "pswd"])
@pytest.mark.parametrize("env_id", ["1", "2", "3"])
@pytest.mark.parametrize("master_ip", ["10.21.10.2", "10.20.1.2"])
def test_upgrade_osd(
        mocker, node_roles, user, password, exception_node, master_ip, env_id):
    auth_mock_client = mocker.patch("octane.util.fuel_client.set_auth_context")
    creds_mock = mocker.patch(
        "octane.handlers.backup_restore.NailgunCredentialsContext")
    mocker.patch(
        "octane.commands.osd_upgrade._get_backup_path",
        return_value="backup_path")
    mocker.patch("octane.magic_consts.OSD_REPOS_UPDATE",
                 [("path", "{admin_ip}")])
    ssh_call_mock = mocker.patch("octane.util.ssh.call")
    preinstall_calls = []
    rollbabk_calls = []
    dpkg_rollbabk_calls = []
    nodes = []
    osd_nodes = []
    hostnames = []
    idx = 0
    call_node = None

    class TestException(Exception):
        pass

    for roles in node_roles:
        node = mocker.Mock()
        hostname = "osd_node.{0}".format(idx)
        node.data = {"roles": roles, "hostname": hostname}
        nodes.append(node)
        if 'ceph-osd' not in roles:
            continue
        osd_nodes.append(node)
        hostnames.append(hostname)
        call_node = call_node or node
        for path, _ in magic_consts.OSD_REPOS_UPDATE:
            preinstall_calls.append((
                mock.call(["cp", path, "backup_path"], node=node),
                exception_node == idx,
            ))
            if exception_node == idx:
                break
            rollbabk_calls.append(
                (mock.call(["mv", "backup_path", path], node=node), False))
        if exception_node == idx:
            break
        preinstall_calls.append(
            (mock.call(["dpkg", "--configure", "-a"], node=node), False))
        dpkg_rollbabk_calls.append(
            (mock.call(["dpkg", "--configure", "-a"], node=node), False))
        idx += 1
    get_nodes_mock = mocker.patch("fuelclient.objects.node.Node.get_all")
    get_nodes_mock.return_value.filter_by_env_id.return_value = nodes

    file_mock = mock.Mock()

    @contextlib.contextmanager
    def updeate_file(*args, **kwargs):
        yield (None, file_mock)

    mocker.patch("octane.util.ssh.update_file", side_effect=updeate_file)
    mocker.patch("octane.util.ssh.sftp")
    mocker.patch(
        "octane.util.helpers.get_astute_dict",
        return_value={"ADMIN_NETWORK": {"ipaddress": master_ip}})
    update_calls = []

    if exception_node is None and idx:
        update_calls.append((
            mock.call(["ceph", "osd", "set", "noout"], node=call_node), False))
        update_calls.append((
            mock.call(
                ['ceph-deploy', 'install', '--release', 'hammer'] + hostnames,
                node=call_node,
                stdout=ssh.PIPE,
                stderr=ssh.PIPE,
            ),
            False
        ))
        for node in osd_nodes:
            update_calls.append(
                (mock.call(['restart', 'ceph-osd-all'], node=node), False))
        update_calls.append((
            mock.call(["ceph", "osd", "unset", "noout"], node=call_node),
            False
        ))
        update_calls.append((
            mock.call(["ceph", "osd", "stat"], node=call_node),
            False
        ))

    calls = \
        preinstall_calls + \
        update_calls + \
        rollbabk_calls + \
        dpkg_rollbabk_calls

    ssh_calls = [i[0] for i in calls]
    ssh_exception_raises = iter([i[1] for i in calls])

    def ssh_call_foo(*args, **kwargs):
        if next(ssh_exception_raises):
            raise TestException()

    ssh_call_mock.side_effect = ssh_call_foo
    if exception_node is not None:
        with pytest.raises(TestException):
            osd_upgrade.upgrade_osd(env_id, user, password)
    else:
        osd_upgrade.upgrade_osd(env_id, user, password)
    ssh_call_mock.assert_has_calls(ssh_calls, any_order=True)
    assert ssh_call_mock.call_count == len(ssh_calls)
    auth_mock_client.assert_called_once_with(creds_mock.return_value)
    creds_mock.assert_called_once_with(user, password)
    get_nodes_mock.return_value.filter_by_env_id.assert_called_once_with(
        env_id)
    if exception_node is not None and idx:
        file_mock.write.assert_called_with(master_ip)
