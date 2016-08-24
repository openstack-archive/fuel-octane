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


@pytest.mark.parametrize("orig_env_id", [None, 1])
@pytest.mark.parametrize("seed_env_id", [None, 2])
@pytest.mark.parametrize("admin_pswd", [None, "pswd"])
def test_osd_cmd_upgrade(
        mocker, octane_app, orig_env_id, seed_env_id, admin_pswd):
    upgrade_osd_mock = mocker.patch("octane.commands.osd_upgrade.upgrade_osd")
    params = ["upgrade-osd"]
    if admin_pswd:
        params += ["--admin-password", admin_pswd]
    if orig_env_id:
        params += [str(orig_env_id)]
    if seed_env_id:
        params += [str(seed_env_id)]
    if orig_env_id and seed_env_id and admin_pswd:
        octane_app.run(params)
        upgrade_osd_mock.assert_called_once_with(
            orig_env_id, seed_env_id, "admin", admin_pswd)
        return
    with pytest.raises(AssertionError):
        octane_app.run(params)
    assert not upgrade_osd_mock.called


@pytest.mark.parametrize("content", ["test_content"])
@pytest.mark.parametrize("directory", ["/dir/path"])
@pytest.mark.parametrize("template", ["templ"])
@pytest.mark.parametrize("generated_name", ["gen_name", "\n\n  gen_name\n\n"])
def test_write_content_to_tmp_file_on_node(
        mocker, content, directory, template, generated_name):
    node = mock.MagicMock()
    sftp_mock = mocker.patch("octane.util.ssh.sftp", return_value=node)
    node.open.__enter__.return_value = node
    short_gen_name = generated_name.strip()
    ssh_mock = mocker.patch("octane.util.ssh.call_output",
                            return_value=generated_name)
    assert short_gen_name == osd_upgrade.write_content_to_tmp_file_on_node(
        node, content, directory, template)
    node.open.assert_called_once_with(short_gen_name, "w")
    node.write(content)
    sftp_mock.assert_called_once_with(node)
    ssh_mock.assert_called_once_with(
        ["mktemp", "-p", directory, "-t", template], node=node)


@pytest.mark.parametrize("nodes_count", [0, 1, 2])
@pytest.mark.parametrize("priority", [100, 200, 300])
@pytest.mark.parametrize("error", [True, False])
def test_applied_repos(mocker, nodes_count, priority, error):

    seed_repos = mock.Mock()
    sftp_mock = mocker.patch("octane.util.ssh.sftp")
    get_pref_mock = mocker.patch(
        "octane.commands.osd_upgrade.apply_preference_for_node",
        side_effect=lambda x, y: x.preference)
    get_source_mock = mocker.patch(
        "octane.commands.osd_upgrade.apply_source_for_node",
        side_effect=lambda x, y: x.source)
    generate_pref_mock = mocker.patch(
        "octane.commands.osd_upgrade.generate_preference_pin")
    generate_source_mock = mocker.patch(
        "octane.commands.osd_upgrade.generate_source_content")

    nodes = [mock.MagicMock() for _ in range(nodes_count)]

    with osd_upgrade.applied_repos(nodes, priority, seed_repos):
        for node in nodes:
            get_source_mock.assert_any_call(
                node, generate_source_mock.return_value)
            get_pref_mock.assert_any_call(
                node, generate_pref_mock.return_value)
        assert not sftp_mock.called

    generate_pref_mock.assert_called_once_with(seed_repos, priority)
    generate_source_mock.assert_called_once_with(seed_repos)

    for node in nodes:
        sftp_mock.assert_any_call(node)
        sftp_mock.return_value.unlink.assert_any_call(node.source)
        sftp_mock.return_value.unlink.assert_any_call(node.preference)


@pytest.mark.parametrize("repos,result", [
    ([{u'priority': None}, {u'priority': None}], 0),
    ([{u'priority': 0}, {u'priority': None}], 0),
    ([{u'priority': 0}, {u'priority': 0}], 0),
    ([{u'priority': 1000}, {u'priority': 0}], 1000),
    ([{u'priority': 1000}, {u'priority': None}], 1000),
])
def test_get_repo_highest_priority(mocker, repos, result):
    env = mock.Mock()
    get_repos_mock = mocker.patch("octane.commands.osd_upgrade.get_env_repos",
                                  return_value=repos)
    assert result == osd_upgrade.get_repo_highest_priority(env)
    get_repos_mock.assert_called_once_with(env)


@pytest.mark.parametrize("orig_id", [2])
@pytest.mark.parametrize("seed_id", [3])
@pytest.mark.parametrize("user", ["user"])
@pytest.mark.parametrize("password", ["password"])
@pytest.mark.parametrize("nodes_count", [0, 10])
@pytest.mark.parametrize("priority", [100, 500])
def test_upgrade_osd(
        mocker, nodes_count, priority, user, password, orig_id, seed_id):
    orig_env = mock.Mock()
    seed_env = mock.Mock()
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
                           side_effect=[orig_env, seed_env])
    mocker.patch("octane.util.env.get_nodes", return_value=iter(nodes))
    mock_creds = mocker.patch(
        "octane.handlers.backup_restore.NailgunCredentialsContext")
    mock_auth_cntx = mocker.patch("octane.util.fuel_client.set_auth_context")
    mock_applied = mocker.patch("octane.commands.osd_upgrade.applied_repos")
    mock_get_priority = mocker.patch(
        "octane.commands.osd_upgrade.get_repo_highest_priority",
        return_value=priority)
    mock_get_env_repos = mocker.patch(
        "octane.commands.osd_upgrade.get_env_repos")
    ssh_call_mock = mocker.patch("octane.util.ssh.call")

    osd_upgrade.upgrade_osd(orig_id, seed_id, user, password)

    mock_creds.assert_called_once_with(user, password)
    mock_auth_cntx.assert_called_once_with(mock_creds.return_value)
    env_get.assert_any_call(orig_id)
    env_get.assert_any_call(seed_id)
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
        mock_get_priority.assert_called_once_with(orig_env)
        mock_applied.assert_called_once_with(
            nodes,
            priority + 1,
            mock_get_env_repos.return_value)
    assert ssh_calls == ssh_call_mock.mock_calls


@pytest.mark.parametrize("repos,result", [
    (
        [
            {
                u'name': u'ubuntu',
                u'section': u'main universe multiverse',
                u'uri': u'http://ubuntu/',
                u'priority': None,
                u'suite': u'trusty',
                u'type': u'deb',
            },
            {
                u'name': u'ubuntu-updates',
                u'section': u'main universe multiverse',
                u'uri': u'http://ubuntu/',
                u'priority': None,
                u'suite': u'trusty-updates',
                u'type': u'deb',
            }
        ],
        "deb http://ubuntu/ trusty main universe multiverse\n"
        "deb http://ubuntu/ trusty-updates main universe multiverse"
    ),
])
def test_generate_source_content(repos, result):
    assert result == osd_upgrade.generate_source_content(repos)


@pytest.mark.parametrize("repos,priority,result", [
    (
        [
            {
                u'name': u'ubuntu',
                u'section': u'main universe multiverse',
                u'uri': u'http://ubuntu/',
                u'priority': None,
                u'suite': u'trusty',
                u'type': u'deb',
            },
            {
                u'name': u'ubuntu-updates',
                u'section': u'main universe multiverse',
                u'uri': u'http://ubuntu/',
                u'priority': None,
                u'suite': u'trusty-updates',
                u'type': u'deb',
            }
        ],
        1000,
        "Package: libcephfs1 librados2 librbd1 python-ceph python-cephfs "
        "python-rados python-rbd ceph ceph-common ceph-fs-common ceph-mds\n"
        "Pin: release a=trusty,n=trusty,l=trusty\n"
        "Pin-Priority: 1000\n"
        "Package: libcephfs1 librados2 librbd1 python-ceph python-cephfs "
        "python-rados python-rbd ceph ceph-common ceph-fs-common ceph-mds\n"
        "Pin: release a=trusty-updates,n=trusty-updates,l=trusty-updates\n"
        "Pin-Priority: 1000"
    ),
])
def test_generate_preference_pin(repos, priority, result):
    assert result == osd_upgrade.generate_preference_pin(repos, priority)


@pytest.mark.parametrize("content", ["content"])
@pytest.mark.parametrize("callmethod,directory,template", [
    (
        osd_upgrade.apply_source_for_node,
        "/etc/apt/sources.list.d/",
        "mos.osd_XXX.list"
    ),
    (
        osd_upgrade.apply_preference_for_node,
        "/etc/apt/preferences.d/",
        "mos.osd_XXX.pref"
    ),
])
def test_apply_source_for_node(
        mocker, node, content, callmethod, directory, template):
    mock_write = mocker.patch(
        "octane.commands.osd_upgrade.write_content_to_tmp_file_on_node")
    assert mock_write.return_value == callmethod(node, content)
    mock_write.assert_called_once_with(node, content, directory, template)


@pytest.mark.parametrize("attrs,result", [
    (
        {
            "editable": {
                "repo_setup": {
                    "repos": {
                        "value": [
                            {
                                u'name': u'ubuntu',
                                u'section': u'main universe multiverse',
                                u'uri': u'http://ubuntu/',
                                u'priority': None,
                                u'suite': u'trusty',
                                u'type': u'deb',
                            },
                            {
                                u'name': u'ubuntu-updates',
                                u'section': u'main universe multiverse',
                                u'uri': u'http://ubuntu/',
                                u'priority': None,
                                u'suite': u'trusty-updates',
                                u'type': u'deb',
                            }
                        ]
                    }
                }
            }
        },
        [
            {
                u'name': u'ubuntu',
                u'section': u'main universe multiverse',
                u'uri': u'http://ubuntu/',
                u'priority': None,
                u'suite': u'trusty',
                u'type': u'deb',
            },
            {
                u'name': u'ubuntu-updates',
                u'section': u'main universe multiverse',
                u'uri': u'http://ubuntu/',
                u'priority': None,
                u'suite': u'trusty-updates',
                u'type': u'deb',
            }
        ]
    ),
])
def test_get_env_repos(attrs, result):
    env = mock.MagicMock()
    env.get_attributes.return_value = attrs
    assert result == osd_upgrade.get_env_repos(env)
