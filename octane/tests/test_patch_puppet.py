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
import collections
import contextlib

import mock
import pytest

from octane.commands.prepare import patch_puppet
from octane import magic_consts
from octane.util import subprocess


@contextlib.contextmanager
def _helper(mocker, os_dir_list=None, is_dir=True, is_dir_list=None):
    os_dir_list = os_dir_list or ['patch_dir']
    mock_list_dir = mocker.patch("os.listdir", return_value=os_dir_list)
    mock_is_dir = mocker.patch("os.path.isdir", return_value=is_dir)
    if not isinstance(is_dir, collections.Iterable):
        is_dir = [is_dir] * len(os_dir_list)
    else:
        assert len(is_dir) == len(os_dir_list)
    yield
    path_arg = '/'.join([magic_consts.CWD, "patches", "puppet"])
    mock_list_dir.assert_called_once_with(path_arg)
    if not is_dir_list:
        is_dir_list = [os_dir_list[i] for i, f in enumerate(is_dir) if f]
    path_args = [mock.call('/'.join([path_arg, i])) for i in is_dir_list]
    assert path_args == mock_is_dir.call_args_list


def test_simple_patch(mocker, mock_subprocess, mock_open):
    with _helper(mocker):
        patch_puppet()
    mock_open.return_value.seek.assert_called_once_with(0)
    kwargs = {
        'stdin': mock_open.return_value,
        'cwd': magic_consts.PUPPET_DIR,
    }
    assert [
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-N', '-p3'], **kwargs)
    ] == mock_subprocess.call_args_list


def test_patch_puppet_nothong_to_revert(mocker, mock_open, mock_subprocess):
    mock_subprocess.side_effect = (
        subprocess.CalledProcessError(1, 'cmd'),
        mock.DEFAULT,
    )
    with _helper(mocker):
        patch_puppet()
    mock_open.return_value.seek.assert_called_once_with(0)
    kwargs = {
        'stdin': mock_open.return_value,
        'cwd': magic_consts.PUPPET_DIR,
    }
    assert [
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-N', '-p3'], **kwargs)
    ] == mock_subprocess.call_args_list


def test_revert_puppet_patch(mocker, mock_open, mock_subprocess):
    with _helper(mocker):
        patch_puppet(True)
    assert not mock_open.return_value.seek.called
    mock_subprocess.assert_called_once_with(
        ['patch', '-R', '-p3'],
        stdin=mock_open.return_value,
        cwd=magic_consts.PUPPET_DIR)


def test_revert_already_reverted_puppet_patch(
        mocker, mock_open, mock_subprocess):
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'cmd')
    with pytest.raises(subprocess.CalledProcessError):
        with _helper(mocker):
            patch_puppet(True)
    assert not mock_open.return_value.seek.called
    mock_subprocess.assert_called_once_with(
        ['patch', '-R', '-p3'],
        stdin=mock_open.return_value,
        cwd=magic_consts.PUPPET_DIR)


def test_double_revert(mocker, mock_open, mock_subprocess):
    with _helper(mocker, ['patch_dir', 'patch_dir_2']):
        patch_puppet(True)
    assert not mock_open.return_value.seek.called
    kwargs = {
        'stdin': mock_open.return_value,
        'cwd': magic_consts.PUPPET_DIR,
    }
    assert [
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-R', '-p3'], **kwargs),
    ] == mock_subprocess.call_args_list


def test_double_apply(mocker, mock_open, mock_subprocess):
    with _helper(mocker, ['patch_dir', 'patch_dir_2']):
        patch_puppet()
    assert [mock.call(0), mock.call(0)] == \
        mock_open.return_value.seek.call_args_list
    kwargs = {
        'stdin': mock_open.return_value,
        'cwd': magic_consts.PUPPET_DIR,
    }
    assert [
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-N', '-p3'], **kwargs),
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-N', '-p3'], **kwargs),
    ] == mock_subprocess.call_args_list


def test_double_apply_one_not_reverted(mocker, mock_open, mock_subprocess):
    mock_subprocess.side_effect = (
        subprocess.CalledProcessError(1, 'cmd'),
        mock.DEFAULT,
        mock.DEFAULT,
        mock.DEFAULT,
    )
    with _helper(mocker, ['patch_dir', 'patch_dir_2']):
        patch_puppet()
    assert [mock.call(0), mock.call(0)] == \
        mock_open.return_value.seek.call_args_list
    kwargs = {
        'stdin': mock_open.return_value,
        'cwd': magic_consts.PUPPET_DIR,
    }
    assert [
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-N', '-p3'], **kwargs),
        mock.call(['patch', '-R', '-p3'], **kwargs),
        mock.call(['patch', '-N', '-p3'], **kwargs),
    ] == mock_subprocess.call_args_list


def test_double_revert_one_already_reverted(
        mocker, mock_open, mock_subprocess):
    mock_subprocess.side_effect = (
        subprocess.CalledProcessError(1, 'cmd'),
        mock.DEFAULT,
    )
    with _helper(mocker,
                 ['patch_dir', 'patch_dir_2'],
                 is_dir_list=['patch_dir']):
        with pytest.raises(subprocess.CalledProcessError):
            patch_puppet(True)
    assert not mock_open.return_value.seek.called
    mock_subprocess.assert_called_once_with(
        ['patch', '-R', '-p3'],
        stdin=mock_open.return_value,
        cwd=magic_consts.PUPPET_DIR)
