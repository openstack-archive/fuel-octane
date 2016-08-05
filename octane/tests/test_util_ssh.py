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

from octane import magic_consts
from octane.util import ssh


@pytest.mark.parametrize('username', ['root', 'test'])
def test_get_sftp(mocker, username):
    mclient = mocker.patch('octane.util.ssh.get_client')
    msftp_client = mocker.patch('paramiko.SFTPClient')
    mtransport = mocker.Mock()
    mchannel = mocker.Mock()
    mclient.return_value.get_transport.return_value = mtransport
    mtransport.open_channel.return_value = mchannel

    mtransport.get_username.return_value = username

    # call not cached version
    ssh._get_sftp.new(mocker.Mock(data={'id': 1, 'hostname': 'test'}))

    if username == 'root':
        msftp_client.from_transport.assert_called_once_with(mtransport)
    else:
        mchannel.exec_command.assert_called_once_with(
            'sudo ' + magic_consts.SFTP_SERVER_BIN)
        msftp_client.assert_called_once_with(mchannel)


@pytest.mark.parametrize("prefix", ["prefix_name"])
@pytest.mark.parametrize("cwd", ["/test/path"])
@pytest.mark.parametrize("patches, error_idx", [
    (["patch_1"], None),
    (["patch_1", "patch_2"], None),
    (["patch_1", "patch_2", "patch_3"], 0),
    (["patch_1", "patch_2", "patch_3"], 1),
    (["patch_1", "patch_2", "patch_3"], 2),
])
@pytest.mark.parametrize("error", [True, False])
def test_applied_patches(mocker, node, mock_open,
                         prefix, patches, cwd, error, error_idx):

    class TestError(Exception):
        pass

    mock_popen = mocker.patch("octane.util.ssh.popen")
    mock_patch_calls = []
    mock_shutil_calls = []
    mock_open_calls = []

    error = error or error_idx is not None
    error_idx = error_idx or len(patches) + 1
    mock_shutil_side_effect = []

    revert_patches = []

    for idx, path in enumerate(patches):
        if idx < error_idx:
            revert_patches.append(path)
        if idx <= error_idx:
            mock_open_calls.append(mock.call(path, "rb"))
            mock_patch_calls.append(mock.call(
                ["patch", "-N", "-p1", "-d", cwd], node=node, stdin=ssh.PIPE
            ))
            mock_shutil_calls.append(mock.call(
                mock_open.return_value,
                mock_popen.return_value.__enter__.return_value.stdin
            ))
        if idx == error_idx:
            mock_shutil_side_effect.append(TestError)
        else:
            mock_shutil_side_effect.append(None)

    revert_patches.reverse()
    for path in revert_patches:
        mock_shutil_side_effect.append(None)
        mock_patch_calls.append(mock.call(
            ["patch", "-R", "-p1", "-d", cwd], node=node, stdin=ssh.PIPE
        ))
        mock_open_calls.append(mock.call(path, "rb"))
        mock_shutil_calls.append(mock.call(
            mock_open.return_value,
            mock_popen.return_value.__enter__.return_value.stdin
        ))

    mock_shutil = mocker.patch(
        "shutil.copyfileobj", side_effect=mock_shutil_side_effect)

    if error:
        with pytest.raises(TestError):
            with ssh.applied_patches(cwd, node, *patches):
                raise TestError
    else:
        with ssh.applied_patches(cwd, node, *patches):
            pass

    assert mock_open_calls == mock_open.call_args_list
    assert mock_patch_calls == mock_popen.call_args_list
    assert mock_shutil_calls == mock_shutil.call_args_list


@pytest.mark.parametrize(
    "editable,result", [
        ({}, None),
        ({'name': {'value': 'a'}, 'password': {'value': 'b'}},
         {'user': 'a', 'password': 'b'}),
    ]
)
def test_ssh_credentials(mocker, editable, result):
    env = mocker.Mock()
    env.get_attributes.return_value = {
        'editable': {'service_user': editable},
    }

    assert ssh.get_env_credentials(env) == result


@pytest.mark.parametrize(
    "editable,result", [
        ({'name': {'value': 'a'}, 'password': {'value': 'b'}},
         {'username': 'a'}),
        ({}, {'username': 'root'}),
    ]
)
def test_get_client_credentials(mocker, editable, result):
    node = mocker.Mock()
    result['key_filename'] = magic_consts.SSH_KEYS

    attrs = {
        'editable': {'service_user': editable},
    }

    ip = '8.8.8.8'

    node.data = {'ip': ip, 'id': 1}
    node.env.get_attributes.return_value = attrs
    mocker.patch('paramiko.SSHClient')
    client = ssh.get_client.new(node)
    client.connect.assert_called_with(ip, **result)
