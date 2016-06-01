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

import contextlib
import io


@contextlib.contextmanager
def mock_update_file(mocker, node, content, expected_content, filename):
    mock_sftp = mocker.patch('octane.util.ssh.sftp')

    old = io.BytesIO(content)
    mock_new = mocker.Mock()
    buf = io.BytesIO()
    mock_new.write = buf.write
    mock_update_file = mocker.patch('octane.util.ssh.update_file')
    mock_update_file.return_value.__enter__.return_value = (old, mock_new)

    yield

    mock_sftp.assert_called_once_with(node)
    mock_update_file.assert_called_once_with(mock_sftp.return_value,
                                             filename)
    assert buf.getvalue() == expected_content
