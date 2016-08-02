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

from octane.commands import osd_upgrade


@pytest.mark.parametrize("env_id", [None, 1])
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


@pytest.mark.parametrize("nodes_count", [0, 1, 2])
@pytest.mark.parametrize("admin_ip,source_tmpl,source", [(
    "10.10.0.1", "source {admin_ip}", "source 10.10.0.1"
)])
@pytest.mark.parametrize("packages,priority,pref_tmpl,pref", [(
    ["pack_1", "pack_2"], 1000, "pref {packages} {priority}",
    "pref pack_1 pack_2 1000"
)])
@pytest.mark.parametrize("error", [True, False])
def test_applied_repos(mocker, nodes_count, admin_ip, source_tmpl, source,
                       packages, priority, pref_tmpl, pref, error):
    mocker.patch("octane.magic_consts.OSD_UPGRADE_REQUIRED_PACKAGES", packages)
    mocker.patch(
        "octane.magic_consts.OSD_UPGADE_PREFERENCE_TEMPLATE", pref_tmpl)
    mocker.patch(
        "octane.magic_consts.OSD_UPGRADE_SOURCE_TEMPLATE", source_tmpl)
    mock_get_astute = mocker.patch(
        "octane.util.helpers.get_astute_dict",
        return_value={"ADMIN_NETWORK": {"ipaddress": admin_ip}})

    nodes = []

    mock_call = mocker.patch("octane.util.ssh.call")
    mock_call_output = mocker.patch("octane.util.ssh.call_output")

    mock_sftp = mocker.patch("octane.util.ssh.sftp", side_effect=lambda x: x)
    return_values = []
    sftp_calls = []

    def update_file_mock_side_effect(node, f_name):
        if f_name == node.source_file:
            return node.source
        elif f_name == node.preference_file:
            return node.preference

    mocker.patch(
        "octane.util.ssh.update_file",
        side_effect=update_file_mock_side_effect)

    for idx in range(nodes_count):
        node = mock.Mock()
        nodes.append(node)
        source_file = "source_file.{0}".format(idx)
        preference_file = "pref_file.{0}".format(idx)
        return_values.append(source_file)
        return_values.append(preference_file)
        sftp_calls.append(node)
        node.source = mock.MagicMock()
        node.preference = mock.MagicMock()
        node.source_file = source_file
        node.preference_file = preference_file
        node.source.__enter__.return_value = (None, node.source)
        node.preference.__enter__.return_value = (None, node.preference)

    mock_call_output.side_effect = return_values

    class TestError(Exception):
        pass

    def check_calls_in_context_manager():
        for node in nodes:
            node.source.write.assert_called_once_with(source)
            node.preference.write.assert_called_once_with(pref)
            mock_call_output.assert_any_call(
                ["mktemp",
                 "-p", "/etc/apt/sources.list.d/",
                 "-t", "mos.osd_XXX.list"],
                node=node)

            mock_call_output.assert_any_call(
                ["mktemp",
                 "-p", "/etc/apt/preferences.d/",
                 "-t", "mos.osd_XXX.pref"],
                node=node)
            mock_sftp.assert_any_call(node)
        assert not mock_call.called
        mock_get_astute.asswert_called_once_with()

    if error:
        with pytest.raises(TestError):
            with osd_upgrade.applied_repos(nodes, priority):
                check_calls_in_context_manager()
                raise TestError
    else:
        with osd_upgrade.applied_repos(nodes, priority):
            check_calls_in_context_manager()

    for node in nodes:
        mock_call.assert_any_call(["rm", node.source_file], node=node)
        mock_call.assert_any_call(["rm", node.preference_file], node=node)


@pytest.mark.parametrize("env_id", [2])
@pytest.mark.parametrize("user", ["user"])
@pytest.mark.parametrize("password", ["password"])
@pytest.mark.parametrize("priority_from, priority_to", [[100, 500]])
@pytest.mark.parametrize("nodes_count", [0, 10])
def test_upgrade_osd(mocker, nodes_count, priority_from,
                     priority_to, user, password, env_id):
    env = mock.Mock()
    nodes = []
    hostnames = []
    restart_calls = []
    for idx in range(nodes_count):
        hostname = "host_{0}".format(idx)
        hostnames.append(hostname)
        node = mock.Mock(data={'hostname': hostname})
        nodes.append(node)
        restart_calls.append(mock.call(["restart", "ceph-osd-all"], node=node))
    env_get = mocker.patch("fuelclient.objects.environment.Environment",
                           return_value=env)
    mocker.patch("octane.util.env.get_nodes", return_value=iter(nodes))
    mock_creds = mocker.patch(
        "octane.handlers.backup_restore.NailgunCredentialsContext")
    mock_auth_cntx = mocker.patch("octane.util.fuel_client.set_auth_context")
    env.get_attributes.return_value = {
        "editable": {
            "repo_setup": {
                "repos": {
                    "value": [{"priority": i}
                              for i in range(priority_from, priority_to + 1)]
                }
            }
        }
    }
    mocker.patch("octane.commands.osd_upgrade.applied_repos")
    ssh_call_mock = mocker.patch("octane.util.ssh.call")

    osd_upgrade.upgrade_osd(env_id, user, password)

    mock_creds.assert_called_once_with(user, password)
    mock_auth_cntx.assert_called_once_with(mock_creds.return_value)
    env_get.assert_called_once_with(env_id)
    ssh_calls = []
    if nodes:
        ssh_calls.append(
            mock.call(["ceph", "osd", "set", "noout"], node=nodes[0]))
        ssh_calls.append(
            mock.call(
                ['ceph-deploy', 'install', '--release', 'hammer'] + hostnames,
                node=nodes[0]))
        ssh_calls.extend(restart_calls)
        ssh_calls.append(
            mock.call(["ceph", "osd", "unset", "noout"], node=nodes[0]))
    assert ssh_calls == ssh_call_mock.mock_calls
