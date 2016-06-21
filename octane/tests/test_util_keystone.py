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

import mock
import pytest

from octane.util import keystone


@contextlib.contextmanager
def verify_update_file(mocker, parameters, writes):
    mock_old = mock.Mock()
    mock_new = mock.Mock()

    mock_update_file = mocker.patch("octane.util.subprocess.update_file")
    mock_update_file.return_value.__enter__.return_value = (mock_old, mock_new)

    mock_iter_params = mocker.patch("octane.util.helpers.iterate_parameters")
    mock_iter_params.return_value = parameters

    expected_writes = [mock.call(call) for call in writes]

    yield mock_update_file

    mock_iter_params.assert_called_once_with(mock_old)
    assert mock_new.write.call_args_list == expected_writes


@pytest.mark.parametrize(("parameters", "writes"), [
    ([
        ("[identity]\n", "identity", None, None),
        ("default_domain_id = b5a5e858092d44ffbe2f3347831c5ca7\n",
         "identity", "default_domain_id", "b5a5e858092d44ffbe2f3347831c5ca7"),
    ], [
        "[identity]\n",
        "#default_domain_id = b5a5e858092d44ffbe2f3347831c5ca7\n",
    ]),
    ([
        ("[identity]\n", "identity", None, None),
    ], [
        "[identity]\n",
    ]),
])
def test_unset_default_domain_id(mocker, parameters, writes):
    with verify_update_file(mocker, parameters, writes) as mock_update_file:
        keystone.unset_default_domain_id("fakefilename")
    mock_update_file.assert_called_once_with("fakefilename")
