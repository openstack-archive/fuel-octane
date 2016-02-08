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

from octane.util import systemd


def test_systemctl_start_timeout(mocker, mock_open):
    test_timeout = "1"
    mock_isdir = mocker.patch("os.path.isdir")
    mock_isdir.return_value = False
    mock_mkdir = mocker.patch("os.mkdir")
    mock_unlink = mocker.patch("os.unlink")
    with systemd.set_systemctl_start_timeout("test_service", test_timeout):
        assert mock_open.called
        assert mock_isdir.called
        assert mock_mkdir.called
    assert mock_unlink.called
