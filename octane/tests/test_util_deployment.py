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

import os

import mock
import pytest

from octane.util import deployment


@pytest.mark.parametrize(("filename", "graph_name", "data", "is_error"), [
    ("/a/b/c/orig/upgrade-db-org.yaml", "upgrade-db-org", {}, True),
    ("/a/b/c/orig/upgrade-db-seed.yaml", "upgrade-db-seed", {}, True),
    ("/a/b/c/seed/upgrade-db-orig.yaml", "upgrade-db-orig", {"a": "b"}, False),
    ("/a/b/c/seed/upgrade-db-seed.yaml", "upgrade-db-seed", {"b": "c"}, False),
])
@pytest.mark.parametrize("env_id", [1, 2])
def test_upload_graph_file_to_env(mocker, filename, graph_name, data, is_error,
                                  env_id):
    mock_load = mocker.patch("octane.util.helpers.load_yaml",
                             return_value=data)
    mock_graph = mocker.patch("fuelclient.v1.graph.GraphClient")
    if is_error:
        with pytest.raises(Exception) as excinfo:
            deployment.upload_graph_file_to_env(filename, env_id)
        assert "Exception: Graph '{0}' is empty.".format(filename) == \
            excinfo.exconly()
    else:
        deployment.upload_graph_file_to_env(filename, env_id)
        mock_graph.return_value.upload.assert_called_once_with(
            data, "clusters", env_id, graph_name)
        mock_load.assert_called_once_with(filename)


@pytest.mark.parametrize(("filenames", "expected"), [
    (["upgrade-db.yaml", "upgrade-db-seed.txt", "upgrade-db", "upgrade.yaml"],
     ["upgrade-db.yaml", "upgrade.yaml"]),
])
@pytest.mark.parametrize("directory", ["/a/b/orig", "/a/b/seed"])
@pytest.mark.parametrize("env_id", [1, 2])
def test_upload_graphs_to_env(mocker, directory, filenames, expected,
                              env_id):
    mock_listdir = mocker.patch("os.listdir", return_value=filenames)
    mock_upload = mocker.patch(
        "octane.util.deployment.upload_graph_file_to_env")
    deployment.upload_graphs_to_env(directory, env_id)
    assert mock_upload.call_args_list == [
        mock.call(os.path.join(directory, filename), env_id)
        for filename in expected
    ]
    mock_listdir.assert_called_once_with(directory)


@pytest.mark.parametrize("orig_id", [1, 2])
@pytest.mark.parametrize("seed_id", [3, 4])
def test_upload_graphs(mocker, orig_id, seed_id):
    mock_upload = mocker.patch("octane.util.deployment.upload_graphs_to_env")
    deployment.upload_graphs(orig_id, seed_id)
    assert mock_upload.call_args_list == [
        mock.call(
            "/var/www/nailgun/octane_code/puppet/octane_tasks/graphs/orig",
            orig_id),
        mock.call(
            "/var/www/nailgun/octane_code/puppet/octane_tasks/graphs/seed",
            seed_id),
    ]


@pytest.mark.parametrize(("statuses", "is_error", "is_timeout"), [
    (["pending", "running", "ready"], False, False),
    (["pending", "running"], False, True),
    (["pending", "pending"], False, True),
    (["pending", "running", "error"], True, False),
])
@pytest.mark.parametrize("graph_name", ["update-db-orig", "upgrade-db-seed"])
@pytest.mark.parametrize("env_id", [1, 2])
def test_execute_graph_and_wait(mocker, statuses, graph_name, env_id, is_error,
                                is_timeout):
    def execute_graph():
        deployment.execute_graph_and_wait(graph_name, env_id,
                                          attempts=attempts)

    mocker.patch("time.sleep")
    mock_status = mock.PropertyMock(side_effect=statuses)
    mock_task = mock.Mock(id=123)
    type(mock_task).status = mock_status
    mock_graph = mocker.patch("fuelclient.v1.graph.GraphClient")
    mock_graph.return_value.execute.return_value = mock_task

    attempts = len(statuses)
    if is_error:
        with pytest.raises(Exception) as excinfo:
            execute_graph()
        assert excinfo.exconly().startswith(
            "Exception: Task 123 with graph {0}".format(graph_name))
    elif is_timeout:
        with pytest.raises(Exception) as excinfo:
            execute_graph()
        assert excinfo.exconly().startswith("Exception: Timeout waiting of")
    else:
        execute_graph()
    mock_graph.return_value.execute.assert_called_once_with(
        env_id, graph_types=[graph_name], nodes=None)
    assert mock_status.call_count == attempts


@pytest.mark.parametrize(("graphs", "expected_names"), [
    (
        [
            {"relations": [{"type": "upgrade-orig"}]},
            {"relations": [{"type": "upgrade-seed"}]},
        ],
        ["upgrade-orig", "upgrade-seed"],
    ),
    ([], []),
])
@pytest.mark.parametrize("env_id", [1, 2])
def test_get_cluster_graph_names(mocker, graphs, expected_names, env_id):
    mock_graph = mocker.patch("fuelclient.v1.graph.GraphClient")
    mock_graph.return_value.list.return_value = graphs
    names = deployment.get_cluster_graph_names(env_id)
    assert names == expected_names
    mock_graph.return_value.list.assert_called_once_with(env_id)
