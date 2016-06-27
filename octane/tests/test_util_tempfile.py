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

from octane.util import tempfile


@pytest.mark.parametrize("dir", ["dir_1", "dir_2", None])
@pytest.mark.parametrize("prefix", ["prefix_1", "prefix_2", None])
def test_get_tempname(mocker, dir, prefix):
    fd = mock.Mock()
    tmp_file_name = mock.Mock()
    mock_mkstemp = mocker.patch(
        "tempfile.mkstemp",
        return_value=(fd, tmp_file_name))
    os_close_mock = mocker.patch("os.close")
    assert tmp_file_name == tempfile.get_tempname(dir, prefix)
    if prefix:
        mock_mkstemp.assert_called_once_with(dir=dir, prefix=prefix)
    else:
        mock_mkstemp.assert_called_once_with(dir=dir)
    os_close_mock.assert_called_once_with(fd)


@pytest.mark.parametrize("is_exception", [True, False])
@pytest.mark.parametrize("prefix", [None, "prefix"])
def test_temp_dir(mocker, is_exception, prefix):

    class TestException(Exception):
        pass

    kwargs = {}
    if prefix is not None:
        kwargs['prefix'] = prefix

    temp_dir_name = mock.Mock()
    mkdtemp_mock = mocker.patch("tempfile.mkdtemp", return_value=temp_dir_name)
    rm_tree_mock = mocker.patch("shutil.rmtree")
    if is_exception:
        with pytest.raises(TestException):
            with tempfile.temp_dir(**kwargs):
                raise TestException
    else:
        with tempfile.temp_dir(**kwargs):
            pass
    mkdtemp_mock.assert_called_once_with(**kwargs)
    rm_tree_mock.assert_called_once_with(temp_dir_name)
