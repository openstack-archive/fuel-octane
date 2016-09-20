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

import io
import itertools

import mock
import pytest

from octane.util import db
from octane.util import ssh


def test_mysqldump_from_env(mocker, mock_open, mock_subprocess, mock_ssh_popen,
                            node):
    test_contents = b'test_contents\nhere'
    buf = io.BytesIO()

    mock_open.return_value.write.side_effect = buf.write

    get_one_node_of = mocker.patch('octane.util.env.get_one_node_of')
    get_one_node_of.return_value = node

    proc = mock_ssh_popen.return_value.__enter__.return_value
    proc.stdout = io.BytesIO(test_contents)

    db.mysqldump_from_env('env', 'controller', ['db1'], 'filename')

    assert not mock_subprocess.called
    mock_ssh_popen.assert_called_once_with(
        ['bash', '-c', mock.ANY], stdout=ssh.PIPE, node=node)
    mock_open.assert_called_once_with('filename', 'wb')
    assert buf.getvalue() == test_contents


def test_mysqldump_restore_to_env(mocker, mock_open, mock_subprocess,
                                  mock_ssh_popen, node):
    test_contents = b'test_contents\nhere'
    buf = io.BytesIO()

    mock_open.return_value = io.BytesIO(test_contents)

    get_one_node_of = mocker.patch('octane.util.env.get_one_node_of')
    get_one_node_of.return_value = node

    proc = mock_ssh_popen.return_value.__enter__.return_value
    proc.stdin.write.side_effect = buf.write

    db.mysqldump_restore_to_env('env', 'controller', 'filename')

    assert not mock_subprocess.called
    mock_ssh_popen.assert_called_once_with(
        ['sh', '-c', mock.ANY], stdin=ssh.PIPE, node=node)
    mock_open.assert_called_once_with('filename', 'rb')
    assert buf.getvalue() == test_contents


def test_db_sync(mocker, node, mock_subprocess, mock_ssh_call):
    get_one_controller = mocker.patch('octane.util.env.get_one_controller')
    get_one_controller.return_value = node

    fix_migration_mock = mocker.patch("octane.util.db.fix_neutron_migrations")

    db.db_sync('env')

    fix_migration_mock.assert_called_once_with(node)

    assert not mock_subprocess.called
    assert all(call[1]['parse_levels']
               for call in mock_ssh_call.call_args_list)
    assert all(call[1]['node'] == node
               for call in mock_ssh_call.call_args_list)


@pytest.mark.parametrize(("version", "result"), [
    ("6.1", False),
    ("7.0", True),
    ("8.0", False),
])
def test_does_perform_flavor_data_migration(version, result):
    env = mock.Mock(data={"fuel_version": version})
    assert db.does_perform_flavor_data_migration(env) == result


@pytest.mark.parametrize(("statuses", "is_error", "is_timeout"), [
    ([(0, 0)], True, False),
    ([(0, 0)], False, False),
    ([(10, 0), (10, 5), (5, 5)], False, False),
    ([(10, 0)], False, True),
])
def test_nova_migrate_flavor_data(mocker, statuses, is_error, is_timeout):
    env = mock.Mock()
    mocker.patch("time.sleep")
    mocker.patch("octane.util.env.get_one_controller")
    mock_output = mocker.patch("octane.util.ssh.call_output")
    attempts = len(statuses)
    mock_output.side_effect = itertools.starmap(FLAVOR_STATUS.format, statuses)
    if is_error:
        mock_output.side_effect = None
        mock_output.return_value = "UNRECOGNIZABLE"
        with pytest.raises(Exception) as excinfo:
            db.nova_migrate_flavor_data(env, attempts=attempts)
        assert excinfo.exconly().startswith(
            "Exception: The format of the migrate_flavor_data command")
    elif is_timeout:
        with pytest.raises(Exception) as excinfo:
            db.nova_migrate_flavor_data(env, attempts=attempts)
        assert excinfo.exconly().startswith(
            "Exception: After {0} attempts flavors data migration"
            .format(attempts))
    else:
        db.nova_migrate_flavor_data(env, attempts=attempts)

FLAVOR_STATUS = "{0} instances matched query, {1} completed"


@pytest.mark.parametrize(("version", "result"), [
    ("6.1", False),
    ("7.0", True),
    ("8.0", False),
])
def test_does_perform_cinder_volume_update_host(version, result):
    env = mock.Mock(data={"fuel_version": version})
    assert db.does_perform_cinder_volume_update_host(env) == result


def test_cinder_volme_update_host(mocker):
    mock_orig_env = mock.Mock()
    mock_new_env = mock.Mock()
    mock_get = mocker.patch("octane.util.env.get_one_controller")
    mock_get_current = mocker.patch("octane.util.db.get_current_host")
    mock_get_new = mocker.patch("octane.util.db.get_new_host")
    mock_ssh = mocker.patch("octane.util.ssh.call")
    db.cinder_volume_update_host(mock_orig_env, mock_new_env)
    mock_ssh.assert_called_once_with(
        ["cinder-manage", "volume", "update_host",
         "--currenthost", mock_get_current.return_value,
         "--newhost", mock_get_new.return_value],
        node=mock_get.return_value, parse_levels=True)


@pytest.mark.parametrize(("func", "content", "expected"), [
    (db.get_current_host, [
        (None, "DEFAULT", None, None),
        (None, "DEFAULT", "host", "fakehost"),
        (None, "DEFAULT", "volume_backend_name", "fakebackend"),
    ], "fakehost#fakebackend"),
    (db.get_new_host, [
        (None, "DEFAULT", None, None),
        (None, "DEFAULT", "host", "fakehost_default"),
        (None, "RBD-backend", None, None),
        (None, "RBD-backend", "volume_backend_name", "fakebackend"),
    ], "fakehost_default@fakebackend#RBD-backend"),
    (db.get_new_host, [
        (None, "DEFAULT", None, None),
        (None, "DEFAULT", "host", "fakehost_default"),
        (None, "RBD-backend", None, None),
        (None, "RBD-backend", "backend_host", "fakehost_specific"),
        (None, "RBD-backend", "volume_backend_name", "fakebackend"),
    ], "fakehost_specific@fakebackend#RBD-backend"),
])
def test_get_hosts_functional(mocker, func, content, expected):
    mock_node = mock.Mock()
    mocker.patch("octane.util.ssh.sftp")
    mock_iter = mocker.patch("octane.util.helpers.iterate_parameters")
    mock_iter.return_value = content
    result = func(mock_node)
    assert expected == result
