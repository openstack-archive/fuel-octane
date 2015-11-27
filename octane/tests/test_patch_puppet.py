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

    def __init__(self, raise_exception_on_revert, revert, *args, **kwargs):
        super(MockFile, self).__init__(*args, **kwargs)
        self.seek_point = 0
        self.seek_call_count = 0
        self.raise_exception_on_revert = raise_exception_on_revert
        self.revert = revert
        self.call_args = []

    def seek(self, point):
        self.seek_point = point
        self.seek_call_count += 1

    def read(self):
        self.seek_point = 100

    def assert_calls(self):
        kwargs = {'stdin': self, 'cwd': magic_consts.PUPPET_DIR}
        args = [((["patch", "-R", "-p3"], ), kwargs), ]
        if not self.revert:
            args.append(((["patch", "-N", "-p3"], ), kwargs))
        assert args == self.call_args


def _read_in_subprocess(*args, **kwargs):
    stdin = kwargs['stdin']
    stdin.call_args.append((args, kwargs))
    assert 0 == stdin.seek_point
    if stdin.raise_exception_on_revert and '-R' in args[0]:
        raise subprocess.CalledProcessError(1, 'cmd')
    stdin.read()
    return mock.DEFAULT


@pytest.mark.parametrize("revert, patch_dirs", [
    # revert, [(is_dir, is_exception_on_revert), ...]
    (False, [(True, False)]),
    (False, [(False, False), (False, False)]),
    (False, [(False, False), (True, False)]),
    (False, [(True, False), (False, False)]),
    (False, [(True, False), (True, False)]),
    (False, [(True, True), (True, True)]),
    (True, [(True, False)]),
    (True, [(False, False), (True, False)]),
    (True, [(True, False), (False, False)]),
    (True, [(True, False), (True, False)]),
])
def test_simple_patch(mocker,
                      mock_subprocess,
                      mock_open,
                      revert,
                      patch_dirs):
    os_dirs = []
    is_dir_list = []
    patch_files = []
    for indx, (is_dir, is_exception_on_revert) in enumerate(patch_dirs):
        patch_dir = "patch_{0}".format(indx)
        os_dirs.append(patch_dir)
        is_dir_list.append(is_dir)
        if is_dir:
            patch_files.append(MockFile(is_exception_on_revert, revert))
    mock_list_dir = mocker.patch("os.listdir", return_value=os_dirs)
    mock_is_dir = mocker.patch("os.path.isdir", side_effect=is_dir_list)
    mock_open.return_value.__enter__.side_effect = patch_files
    mock_subprocess.side_effect = _read_in_subprocess
    patch_puppet(revert)
    path_arg = '/'.join([magic_consts.CWD, "patches", "puppet"])
    mock_list_dir.assert_called_once_with(path_arg)
    path_args = [mock.call('/'.join([path_arg, i])) for i in os_dirs]
    assert path_args == mock_is_dir.call_args_list
    for mock_open_file in patch_files:
        mock_open_file.assert_calls()
