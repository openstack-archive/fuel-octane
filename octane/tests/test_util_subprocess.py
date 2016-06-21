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

from octane.util import subprocess


class _TestException(Exception):
    pass


@pytest.mark.parametrize(("exception", "reraise", "calls"), [
    (None, False, [
        mock.call.stat("/fake/filename"),
        mock.call.chmod("/temp/filename", 0o640),
        mock.call.chown("/temp/filename", 2, 3),
        mock.call.rename("/fake/filename", "/fake/filename.bak"),
        mock.call.rename("/temp/filename", "/fake/filename"),
        mock.call.unlink("/fake/filename.bak"),
    ]),
    (subprocess.DontUpdateException, False, [
        mock.call.unlink("/temp/filename"),
    ]),
    (_TestException, True, [
        mock.call.unlink("/temp/filename"),
    ]),
])
def test_update_file(mocker, mock_open, exception, reraise, calls):
    mock_tempfile = mocker.patch("octane.util.tempfile.get_tempname")
    mock_tempfile.return_value = "/temp/filename"

    mock_old = mock.MagicMock()
    mock_new = mock.MagicMock()

    mock_open.side_effect = [mock_old, mock_new]

    mock_os = mock.Mock()
    os_methods = ["unlink", "stat", "chmod", "chown", "rename"]
    for method in os_methods:
        mocker.patch("os." + method, new=getattr(mock_os, method))

    mock_os.stat.return_value.configure_mock(
        st_mode=0o640,
        st_uid=2,
        st_gid=3,
    )

    if reraise:
        with pytest.raises(exception):
            with subprocess.update_file("/fake/filename"):
                raise exception
    else:
        with subprocess.update_file("/fake/filename"):
            if exception is not None:
                raise exception

    assert mock_os.mock_calls == calls
