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

from octane.util import ssh


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


creds = {'name': {'value': 'a'}, 'password': {'value': 'b'}}


@pytest.mark.parametrize(
    "editable,generated,result", [
        ({}, {}, KeyError),
        ({}, creds, {'user': 'a', 'password': 'b'}),
        (creds, {}, {'user': 'a', 'password': 'b'}),
        ({'name': {'value': 'b'}}, creds, {'user': 'b', 'password': 'b'}),
    ]
)
def test_ssh_credentials(mocker, editable, generated, result):
    env = mocker.Mock()
    env.get_attributes.return_value = {
        'editable': {'service_user': editable},
        'generated': {'service_user': generated},
    }

    if isinstance(result, dict):
        assert ssh.get_env_credentials(env) == result
    else:
        with pytest.raises(result):
            ssh.get_env_credentials(env)


def test_ssh_credentials_fallback(mocker):
    env = mocker.Mock()
    env.get_attributes.return_value = {'editable': {}, 'generated': {}}
    assert ssh.get_env_credentials(env) is None
