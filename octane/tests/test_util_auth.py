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

from octane.handlers import backup_restore
from octane.util import auth


class TestException(Exception):
    pass


@pytest.mark.parametrize("exc_on_apply", [True, False])
def test_set_astute_password(mocker, mock_open, exc_on_apply):
    fd_mock = mock.Mock()
    close_mock = mocker.patch("os.close")
    mkstemp_mock = mocker.patch(
        "tempfile.mkstemp",
        return_value=(fd_mock, "/etc/fuel/.astute.yaml.bac"))
    mock_copy = mocker.patch("shutil.copy2")
    mock_move = mocker.patch("shutil.move")
    yaml_load = mocker.patch(
        "yaml.load", return_value={"FUEL_ACCESS": {"password": "dump_pswd"}})
    yaml_dump = mocker.patch("yaml.safe_dump")
    context = backup_restore.NailgunCredentialsContext(
        user="admin", password="user_pswd")
    if exc_on_apply:
        with pytest.raises(TestException):
            with auth.set_astute_password(context):
                raise TestException("text exception")
    else:
        with auth.set_astute_password(context):
            pass
    assert mock_open.call_args_list == [
        mock.call("/etc/fuel/astute.yaml", "r"),
        mock.call("/etc/fuel/astute.yaml", "w"),
    ]
    yaml_load.assert_called_once_with(mock_open.return_value)
    yaml_dump.assert_called_once_with(
        {'FUEL_ACCESS': {'password': 'user_pswd'}},
        mock_open.return_value,
        default_flow_style=False)
    mock_copy.assert_called_once_with("/etc/fuel/astute.yaml",
                                      "/etc/fuel/.astute.yaml.bac")
    mock_move.assert_called_once_with("/etc/fuel/.astute.yaml.bac",
                                      "/etc/fuel/astute.yaml")
    mkstemp_mock.assert_called_once_with(
        dir="/etc/fuel", prefix=".astute.yaml.octane")
    close_mock.assert_called_once_with(fd_mock)
