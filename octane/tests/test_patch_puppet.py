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
from contextlib import nested
import mock
from octane.commands.prepare import patch_puppet
from octane import magic_consts
from octane.util import subprocess
import pytest


def test_simple_patch(mocker, mock_subprocess, mock_open):
    with nested(mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_list_dir, mock_is_dir):
        patch_puppet()
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 1 == mock_is_dir.call_count
        assert 1 == patch_file.seek.call_count
        assert 2 == mock_subprocess.call_count
        revert_cmd, apply_cmd = mock_subprocess.call_args_list
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd
        assert ((['patch', '-N', '-p3'], ), kwargs) == apply_cmd


def test_patch_puppet_nothong_to_revert(mocker, mock_open, *args, **kwargs):
    with nested(mock.patch("octane.commands.prepare.subprocess.call"),
                mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_call, mock_list_dir, mock_is_dir):
        mock_call.side_effect = (
            subprocess.CalledProcessError(1, 'cmd'),
            None
        )
        patch_puppet()
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 1 == mock_is_dir.call_count
        assert 1 == patch_file.seek.call_count
        assert 2 == mock_call.call_count
        revert_cmd, apply_cmd = mock_call.call_args_list
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd
        assert ((['patch', '-N', '-p3'], ), kwargs) == apply_cmd


def test_revert_puppet_patch(mock_open, mock_subprocess, *args, **kwargs):
    with nested(mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_list_dir, mock_is_dir):
        patch_puppet(True)
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 1 == mock_is_dir.call_count
        assert not patch_file.seek.called
        assert 1 == mock_subprocess.call_count
        revert_cmd = mock_subprocess.call_args
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd


def test_revert_already_reverted_puppet_patch(mock_open):
    with nested(mock.patch("octane.commands.prepare.subprocess.call"),
                mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_call, mock_list_dir, mock_is_dir):
        mock_call.side_effect = subprocess.CalledProcessError(1, 'cmd')
        with pytest.raises(subprocess.CalledProcessError):
            patch_puppet(True)
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 1 == mock_is_dir.call_count
        assert not patch_file.seek.called
        assert 1 == mock_call.call_count
        revert_cmd = mock_call.call_args
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd


def test_double_revert(mock_open):
    with nested(mock.patch("octane.commands.prepare.subprocess.call"),
                mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir', 'patch_dir_2']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_call, mock_list_dir, mock_is_dir):
        patch_puppet(True)
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 2 == mock_is_dir.call_count
        assert not patch_file.seek.called
        assert 2 == mock_call.call_count
        revert_cmd = mock_call.call_args
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd


def test_double_apply(mock_open):
    with nested(mock.patch("octane.commands.prepare.subprocess.call"),
                mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir', 'patch_dir_2']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_call, mock_list_dir, mock_is_dir):

        patch_puppet()
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 2 == mock_is_dir.call_count
        assert 2 == patch_file.seek.call_count
        assert 4 == mock_call.call_count
        revert_cmd_1, apply_cmd_1, revert_cmd_2, apply_cmd_2 = \
            mock_call.call_args_list
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd_1
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd_2
        assert ((['patch', '-N', '-p3'], ), kwargs) == apply_cmd_1
        assert ((['patch', '-N', '-p3'], ), kwargs) == apply_cmd_2


def test_double_apply_one_not_reverted(mock_open):
    with nested(mock.patch("octane.commands.prepare.subprocess.call"),
                mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir', 'patch_dir_2']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_call, mock_list_dir, mock_is_dir):

        mock_call.side_effect = (
            subprocess.CalledProcessError(1, 'cmd'),
            None,
            None,
            None
        )

        patch_puppet()
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 2 == mock_is_dir.call_count
        assert 2 == patch_file.seek.call_count
        assert 4 == mock_call.call_count
        revert_cmd_1, apply_cmd_1, revert_cmd_2, apply_cmd_2 = \
            mock_call.call_args_list
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd_1
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd_2
        assert ((['patch', '-N', '-p3'], ), kwargs) == apply_cmd_1
        assert ((['patch', '-N', '-p3'], ), kwargs) == apply_cmd_2


def test_double_revert_one_already_reverted(mock_open):
    with nested(mock.patch("octane.commands.prepare.subprocess.call"),
                mock.patch("octane.commands.prepare.os.listdir",
                           return_value=['patch_dir', 'patch_dir_2']),
                mock.patch("octane.commands.prepare.os.path.isdir",
                           return_value=True)) as (
            mock_call, mock_list_dir, mock_is_dir):

        mock_call.side_effect = (
            subprocess.CalledProcessError(1, 'cmd'),
            None,
        )

        with pytest.raises(subprocess.CalledProcessError):
            patch_puppet(True)
        patch_file = mock_open()
        assert 1 == mock_list_dir.call_count
        assert 1 == mock_is_dir.call_count
        assert not patch_file.seek.called
        assert 1 == mock_call.call_count
        revert_cmd = mock_call.call_args
        kwargs = {
            'stdin': patch_file,
            'cwd': magic_consts.PUPPET_DIR,
        }
        assert ((['patch', '-R', '-p3'], ), kwargs) == revert_cmd
