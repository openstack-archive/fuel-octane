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

from octane.commands import preupgrade_compute
from octane import magic_consts


@pytest.mark.parametrize("cmd,release_id,node_ids", [
    (["preupgrade-compute", "1", "1", "2"], 1, [1, 2]),
    (["preupgrade-compute", "1", "1"], 1, [1]),
])
def test_parser(mocker, octane_app, cmd, release_id, node_ids):
    m = mocker.patch("octane.commands.preupgrade_compute.preupgrade_compute")
    octane_app.run(cmd)
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(release_id, node_ids)


@pytest.mark.parametrize("release_id,node_ids,env_id", [
    (1, [1, 2], 1),
    (1, [1], 1),
])
@pytest.mark.parametrize("version", ["liberty-8.0"])
def test_preupgrade_compute(mocker, release_id, node_ids, env_id, version):
    def _create_node(node_id):
        node = mock.Mock()
        node.id = node_id
        node.env.id = env_id
        node.data = {}
        node.data['roles'] = 'compute'
        mock_nodes_list.append(node)
        return node

    mock_nodes_list = []
    mock_node = mocker.patch("fuelclient.objects.node.Node")
    mock_node.side_effect = _create_node
    mock_release_class = mocker.patch("fuelclient.objects.Release")
    mock_release = mock_release_class.return_value
    mock_release.data = {}
    mock_release.data["version"] = version
    mock_release.data['state'] = "available"
    mock_get_astute_dict = mocker.patch("octane.util.helpers.get_astute_dict")
    mock_get_repos = mocker.patch(
        "octane.commands.preupgrade_compute.get_repos"
    )
    mock_change_repos = mocker.patch(
        "octane.commands.preupgrade_compute.change_repositories"
    )
    mock_stop_services = mocker.patch(
        "octane.commands.preupgrade_compute.stop_compute_services"
    )
    mock_upgrade_packages = mocker.patch("octane.util.apt.upgrade_packages")

    preupgrade_compute.preupgrade_compute(release_id, node_ids)

    assert mock_node.call_args_list == [
        mock.call(node_id) for node_id in node_ids]
    mock_get_astute_dict.assert_called_once_with()
    assert mock_change_repos.call_args_list == [
        mock.call(node, mock_get_repos.return_value)
        for node in mock_nodes_list]
    assert mock_stop_services.call_args_list == [
        mock.call(node) for node in mock_nodes_list]
    assert mock_upgrade_packages.call_args_list == [
        mock.call(node, magic_consts.COMPUTE_PREUPGRADE_PACKAGES.get(version))
        for node in mock_nodes_list]


@pytest.mark.parametrize("release_id,node_ids,env_ids,roles,state,err", [
    (1, [1, 2], [1, 1], ["compute", "compute"], "available", None),
    (1, [1, 2], [1, 1], ["compute", "compute"], "manageonly", None),
    (1, [1, 3], [1, 1], ["compute", "compute"], "unavailable", Exception),
    (1, [1, 2], [1, 2], ["compute", "compute"], "available", Exception),
    (1, [1, 2], [1, 1], ["compute", "controller"], "available", Exception),
])
def test_check_sanity(release_id, node_ids, env_ids, roles, state, err):
    node_list = []
    release = mock.Mock()
    release.id = release_id
    release.data = {}
    release.data["state"] = state
    for node_id, env_id, role in zip(node_ids, env_ids, roles):
        node = mock.Mock()
        node.id = node_id
        node.env.id = env_id
        node.data = {}
        node.data['roles'] = role
        node_list.append(node)
    if err:
        with pytest.raises(err) as exc_info:
            preupgrade_compute.check_sanity(node_list, release)
        if state != "available":
            assert "Release with id {0} is not available (at least " \
                   "manageonly).".format(release_id) in exc_info.value.args[0]
        elif env_ids[0] != env_ids[1]:
            assert "Nodes have different clusters." in exc_info.value.args[0]
        else:
            assert "Preupgrade procedure is available only for " \
                   "compute nodes. Node with id {0} " \
                   "is not a compute.".format(node_ids[1])
    else:
        assert preupgrade_compute.check_sanity(node_list, release) is None


@pytest.mark.parametrize("repos,has_priority", [
    ([{'name': 'test_1', 'priority': None},
      {'name': 'test_2', 'priority': None}], False),
    ([{'name': 'test_1', 'priority': None}, {'priority': 1050}], True),
])
def test_change_repositories(mocker, repos, has_priority):
    node = mock.Mock()
    dirs = ['/etc/apt/sources.list.d', '/etc/apt/preferences.d']
    mock_remove = mocker.patch("octane.util.ssh.remove_all_files_from_dirs")
    mock_sftp = mocker.patch("octane.util.ssh.sftp")
    mock_source = mocker.patch("octane.util.apt.create_repo_source")
    mock_source.return_value = 'filename_source', 'content_source'
    mock_preferences = mocker.patch("octane.util.apt.create_repo_preferences")
    mock_preferences.return_value = 'filename_pref', 'content_pref'
    mock_write_content = mocker.patch("octane.util.ssh.write_content_to_file")
    mock_call = mocker.patch("octane.util.ssh.call")
    preupgrade_compute.change_repositories(node, repos)
    mock_remove.assert_called_once_with(dirs, node)
    mock_source.call_args_list == [mock.call(repo) for repo in repos]
    calls_write = [
        mock.call(mock_sftp, mock_source.return_value) for repo in repos
        ]
    if has_priority:
        mock_preferences.call_args_list == [
            mock.call(repo) for repo in repos if repo['priority']
        ]
        calls_write.append(
            mock.call(mock_sftp, mock_source.return_value)
            for repo in repos if repo['priority']
        )
    mock_write_content.call_args_list == calls_write
    mock_call.assert_called_once_with(['apt-get', 'update'], node=node)


def test_stop_compute_services(mocker):
    node = mock.Mock()
    mock_call = mocker.patch("octane.util.ssh.call")
    preupgrade_compute.stop_compute_services(node)
    mock_call.call_args_list == [
        mock.call(['stop', 'nova-compute'], node=node),
        mock.call(['stop', 'neutron-plugin-openvswitch-agent'], node=node)
    ]


REPOS = [
    {'name': 'ubuntu-security',
     'priority': None,
     'section': 'main universe multiverse',
     'suite': 'trusty-security',
     'type': 'deb',
     'uri': 'http://archive.ubuntu.com/ubuntu/'},
    {'name': 'mos',
     'priority': 1050,
     'section': 'main restricted',
     'suite': 'mos8.0',
     'type': 'deb',
     'uri': 'http://{settings.MASTER_IP}:8080/{cluster.release.version}/'
            'ubuntu/x86_64'},
    {'name': 'mos-updates',
     'priority': 1050,
     'section': 'main restricted',
     'suite': 'mos8.0-updates',
     'type': 'deb',
     'uri': 'http://mirror.fuel-infra.org/mos-repos/'
            'ubuntu/{cluster.release.environment_version}/'},
]

REPOS_WITH_REPLACE_URI = [
    {'name': 'ubuntu-security',
     'priority': None,
     'section': 'main universe multiverse',
     'suite': 'trusty-security',
     'type': 'deb',
     'uri': 'http://archive.ubuntu.com/ubuntu/'},
    {'name': 'mos',
     'priority': 1050,
     'section': 'main restricted',
     'suite': 'mos8.0',
     'type': 'deb',
     'uri': 'http://10.20.0.2:8080/liberty-8.0/ubuntu/x86_64'},
    {'name': 'mos-updates',
     'priority': 1050,
     'section': 'main restricted',
     'suite': 'mos8.0-updates',
     'type': 'deb',
     'uri': 'http://mirror.fuel-infra.org/mos-repos/ubuntu/8.0/'},
]

RELEASE_DATA = {
    'attributes_metadata': {
        'editable': {
            'repo_setup': {
                'repos': {
                    'value': REPOS
                }
            }
        }
    },
    'version': "liberty-8.0",
}


@pytest.mark.parametrize("ip,release_data,repos_with_replace_uri", [
    ("10.20.0.2", RELEASE_DATA, REPOS_WITH_REPLACE_URI)
])
def test_get_repos(ip, release_data, repos_with_replace_uri):
    release = mock.Mock()
    release.data = release_data
    assert preupgrade_compute.get_repos(release, ip) == repos_with_replace_uri
