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


@pytest.mark.parametrize("method,pairs,call_method", [
    (ssh.get_files_from_remote_node, [("remote_path", "local_path")], "get"),
    (ssh.put_files_to_remote_node, [("local_path", "remote_path")], "put"),
])
def test_get_put_files_from_remote_node(mocker, method, pairs, call_method):
    node = mock.Mock()
    sftp_mock = mocker.patch("octane.util.ssh.sftp", return_value=mock.Mock())
    method(node, pairs)
    sftp_mock.assert_called_once_with(node)
    mock_call = getattr(sftp_mock.return_value, call_method)
    assert [mock.call(*i) for i in pairs] == mock_call.call_args_list
