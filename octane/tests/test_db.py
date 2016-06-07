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

from octane import magic_consts
from octane.util import db
from octane.util import ssh


def test_mysqldump_from_env(mocker, mock_open, mock_subprocess, mock_ssh_popen,
                            node):
    test_contents = b'test_contents\nhere'
    buf = io.BytesIO()

    mock_open.return_value.write.side_effect = buf.write

    get_one_controller = mocker.patch('octane.util.env.get_one_controller')
    get_one_controller.return_value = node

    proc = mock_ssh_popen.return_value.__enter__.return_value
    proc.stdout = io.BytesIO(test_contents)

    db.mysqldump_from_env('env', ['db1'], 'filename')

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

    get_one_controller = mocker.patch('octane.util.env.get_one_controller')
    get_one_controller.return_value = node

    proc = mock_ssh_popen.return_value.__enter__.return_value
    proc.stdin.write.side_effect = buf.write

    db.mysqldump_restore_to_env('env', 'filename')

    assert not mock_subprocess.called
    mock_ssh_popen.assert_called_once_with(
        ['sh', '-c', mock.ANY], stdin=ssh.PIPE, node=node)
    mock_open.assert_called_once_with('filename', 'rb')
    assert buf.getvalue() == test_contents


def test_db_sync(mocker, node, mock_subprocess, mock_ssh_call):
    get_one_controller = mocker.patch('octane.util.env.get_one_controller')
    get_one_controller.return_value = node

    applied_patches = mocker.patch("octane.util.ssh.applied_patches")

    db.db_sync('env')

    applied_patches.assert_called_once_with(
        magic_consts.NOVA_PATCH_PREFIX_DIR, node, *magic_consts.NOVA_PATCHES)

    assert not mock_subprocess.called
    assert all(call[1]['parse_levels']
               for call in mock_ssh_call.call_args_list)
    assert all(call[1]['node'] == node
               for call in mock_ssh_call.call_args_list)
