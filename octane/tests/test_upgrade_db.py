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

from octane.commands import upgrade_db


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.upgrade_db.upgrade_db')
    octane_app.run(["upgrade-db", "1", "2", "--db_role_name", "3"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2, '3')


def test_parser_with_graph(mocker, octane_app):
    m = mocker.patch("octane.commands.upgrade_db.upgrade_db_with_graph")
    octane_app.run(["upgrade-db", "--with-graph", "1", "2"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2)


def test_parser_exclusive_group(mocker, octane_app):
    mocker.patch("octane.commands.upgrade_db.upgrade_db")
    mocker.patch("octane.commands.upgrade_db.upgrade_db_with_graph")
    with pytest.raises(AssertionError):
        octane_app.run(["upgrade-db", "--with-graph", "--db_role_name", "db",
                        "1", "2"])


@pytest.mark.parametrize(("calls", "graph_names", "catch"), [
    # Orig is fine, seed is fine and there is no need to rollback.
    (
        [
            ("upgrade-db", False),
            ("upgrade-db", False),
        ],
        ["upgrade-db", "upgrade-db-rollback", "upgrade-db"],
        None,
    ),
    # Orig is fine, seed fails and there is no rollback.
    (
        [
            ("upgrade-db", False),
            ("upgrade-db", True),
        ],
        ["upgrade-db", "upgrade-db"],
        "upgrade-db",
    ),
    # Orig is fine, seed fails and rollback is fine.
    (
        [
            ("upgrade-db", False),
            ("upgrade-db", True),
            ("upgrade-db-rollback", False),
        ],
        ["upgrade-db", "upgrade-db-rollback", "upgrade-db"],
        "upgrade-db",
    ),
    # Orig is fine, seed fails and rollback fails too.
    (
        [
            ("upgrade-db", False),
            ("upgrade-db", True),
            ("upgrade-db-rollback", True),
        ],
        ["upgrade-db", "upgrade-db-rollback", "upgrade-db"],
        "upgrade-db-rollback",
    ),
    # Orig fails and there is no rollback.
    (
        [
            ("upgrade-db", True),
        ],
        ["upgrade-db", "upgrade-db"],
        "upgrade-db",
    ),
    # Orig fails, rollback is fine.
    (
        [
            ("upgrade-db", True),
            ("upgrade-db-rollback", False),
        ],
        ["upgrade-db", "upgrade-db-rollback", "upgrade-db"],
        "upgrade-db",
    ),
    # Orig fails, rollback is also fails.
    (
        [
            ("upgrade-db", True),
            ("upgrade-db-rollback", True),
        ],
        ["upgrade-db", "upgrade-db-rollback", "upgrade-db"],
        "upgrade-db-rollback",
    ),
])
def test_upgrade_db_with_graph(mocker, calls, graph_names, catch):
    class ExecutionError(Exception):
        pass

    def execute_graph(graph_name, env_id):
        assert graph_name in results, \
            "Unxpected execution of the graph {0}".format(graph_name)
        result = results[graph_name]
        if result is not None:
            raise result
        return mock.DEFAULT

    results = {
        graph_name: ExecutionError(graph_name) if is_error else None
        for graph_name, is_error in calls
    }
    expected_exception = None
    if catch is not None:
        expected_exception = results[catch]

    mocker.patch("octane.util.deployment.upload_graphs")
    mocker.patch("octane.util.deployment.execute_graph_and_wait",
                 side_effect=execute_graph)
    mocker.patch("octane.util.deployment.get_cluster_graph_names",
                 return_value=graph_names)

    if expected_exception is not None:
        with pytest.raises(ExecutionError) as excinfo:
            upgrade_db.upgrade_db_with_graph(1, 2)
        assert excinfo.value is expected_exception
    else:
        upgrade_db.upgrade_db_with_graph(1, 2)
