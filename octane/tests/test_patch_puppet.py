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

from octane.commands.prepare import patch_puppet
from octane import magic_consts
from octane.util import subprocess


class MockFile(mock.MagicMock):

    def __init__(self, raise_exception_on_revert, is_patched, *args, **kwargs):
        super(MockFile, self).__init__(*args, **kwargs)
        self.seek_point = 0
        self.seek_call_count = 0
        self.raise_exception_on_revert = raise_exception_on_revert
        self.is_patched = is_patched

    def assert_seek_called_once(self):
        assert self.seek_call_count == 1

    def seek(self, point):
        self.seek_point = point
        self.seek_call_count += 1

    def read(self):
        self.seek_point = 100


def _read_in_subprocess(*args, **kwargs):
    stdin = kwargs['stdin']
    assert 0 == stdin.seek_point
    if stdin.raise_exception_on_revert and '-R' in args[0]:
        raise subprocess.CalledProcessError(1, 'cmd')
    stdin.read()
    return mock.DEFAULT


@pytest.mark.parametrize(
    "patch_dirs,revert",
    [
        (
            # [(name_dir, is_dir, is_patched, is_exception_on_revert), ... ]
            [("patch_dir", True, True, False)],
            False,
        ),
        (
            [
                ("patch_dir", True, True, False),
                ("patch_dir_2", False, False, False),
            ],
            False,
        ),
        (
            [
                ("patch_dir", True, True, False),
                ("patch_dir_2", True, True, False),
            ],
            False,
        ),
        (
            [
                ("patch_dir", False, False, False),
                ("patch_dir_2", False, False, False),
            ],
            False,
        ),
        (
            [
                ("patch_dir", False, False, False),
                ("patch_dir_2", True, True, False),
            ],
            False,
        ),
        (
            [
                ("patch_dir", True, False, False),
            ],
            True,
        ),
        (
            [
                ("patch_dir", True, False, False),
                ("patch_dir_2", True, False, False),
            ],
            True,
        ),
        (
            [
                ("patch_dir", False, False, False),
                ("patch_dir_2", True, False, False),
            ],
            True,
        ),
        (
            [
                ("patch_dir", True, False, False),
                ("patch_dir_2", False, False, False),
            ],
            True,
        ),
        (
            [
                ("patch_dir", True, True, True),
                ("patch_dir_2", True, True, True),
            ],
            False,
        ),
    ]
)
def test_simple_patch(mocker,
                      mock_subprocess,
                      mock_open,
                      patch_dirs,
                      revert):
    os_dirs = []
    is_dir_list = []
    os_opened_dirs = []
    patch_files = []
    for patch_dir, is_dir, is_patched, is_exception_on_revert in patch_dirs:
        os_dirs.append(patch_dir)
        is_dir_list.append(is_dir)
        if not is_dir:
            continue
        os_opened_dirs.append(patch_dir)
        patch_files.append(MockFile(is_exception_on_revert, is_patched))
    mock_list_dir = mocker.patch("os.listdir", return_value=os_dirs)
    mock_is_dir = mocker.patch("os.path.isdir", side_effect=is_dir_list)
    mocker.patch("os.path.isfile", return_value=True)
    mock_open.return_value.__enter__.side_effect = patch_files
    mock_subprocess.side_effect = _read_in_subprocess
    patch_puppet(revert)
    path_arg = '/'.join([magic_consts.CWD, "patches", "puppet"])
    mock_list_dir.assert_called_once_with(path_arg)
    path_args = [mock.call('/'.join([path_arg, i])) for i in os_dirs]
    assert path_args == mock_is_dir.call_args_list
    calls_list = []
    for mock_open_file in patch_files:
        if mock_open_file.is_patched:
            mock_open_file.assert_seek_called_once()
        else:
            assert not mock_open_file.called
        calls_list.append(
            mock.call(
                ["patch", "-R", "-p3"],
                stdin=mock_open_file,
                cwd=magic_consts.PUPPET_DIR)
        )
        if not revert:
            calls_list.append(
                mock.call(
                    ["patch", "-N", "-p3"],
                    stdin=mock_open_file,
                    cwd=magic_consts.PUPPET_DIR)
            )
    assert calls_list == mock_subprocess.call_args_list
