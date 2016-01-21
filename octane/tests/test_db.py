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

import mock

from octane.commands import upgrade_db
from octane.util import db
from octane.util import env
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

    db.db_sync('env')

    assert not mock_subprocess.called
    assert all(call[1]['parse_levels']
               for call in mock_ssh_call.call_args_list)
    assert all(call[1]['node'] == node
               for call in mock_ssh_call.call_args_list)


def test_upgrade_db(mocker, node):
    FAKE_ROLE_NAME = 'some_name'

    mysqldump_restore = mocker.patch('octane.util.db.mysqldump_restore_to_env')
    delete_fuel_res = mocker.patch('octane.util.env.delete_fuel_resources')
    mysqldump_from_env = mocker.patch('octane.util.db.mysqldump_from_env')
    disable_apis = mocker.patch('octane.util.maintenance.disable_apis')
    get_databases = mocker.patch('octane.util.db.get_databases')
    db_sync = mocker.patch('octane.util.db.db_sync')
    copy_backup = mocker.patch('shutil.copy')

    stop_cor = mocker.patch('octane.util.maintenance.stop_corosync_services')
    stop_ups = mocker.patch('octane.util.maintenance.stop_upstart_services')

    upgrade_db.upgrade_db('1', '2', FAKE_ROLE_NAME)

    copy_backup.assert_called_once_with('/tmp/dbs.original.sql.gz',
                                        '/tmp/dbs.original.cluster_1.sql.gz')

    mysqldump_from_env.assert_called_once_with(
        mock.ANY, FAKE_ROLE_NAME, mock.ANY, '/tmp/dbs.original.sql.gz')

    mysqldump_restore.assert_called_once_with(
        mock.ANY, FAKE_ROLE_NAME, '/tmp/dbs.original.sql.gz')

    delete_fuel_res.assert_called_once_with(mock.ANY)
    get_databases.assert_called_once_with(mock.ANY)
    disable_apis.assert_called_once_with(mock.ANY)
    stop_cor.assert_called_once_with(mock.ANY)
    stop_ups.assert_called_once_with(mock.ANY)
    db_sync.assert_called_once_with(mock.ANY)


class FakeEnv(object):
    data = {'id': 'some_id'}


def fake_nodes():
    for node in ['node1', 'node2']:
        yield node


def test_get_one_node_of(mocker):
    get_nodes = mocker.patch('octane.util.env.get_nodes')
    get_nodes.return_value = fake_nodes()

    fake_env = FakeEnv()

    node = env.get_one_node_of(fake_env, 'controller')
    assert node == 'node1'
