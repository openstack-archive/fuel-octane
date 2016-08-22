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

import json
import mock
import pytest

from octane.util import mcollective
from octane.util import subprocess


def test_get_mco_ping_status(mocker):
    popen_mock = mock.MagicMock()
    popen_mock.return_value.__enter__.return_value = popen_mock
    data = {"a": 1, "test": True, "b": 2}
    popen_mock.stdout.read.return_value = json.dumps(data)
    popen_patch = mocker.patch(
        "octane.util.docker.in_container", new=popen_mock)
    assert data == mcollective.get_mco_ping_status()
    popen_patch.assert_called_once_with(
        'astute',
        ["mco", "rpc", "rpcutil", "ping", "--json"],
        stdout=subprocess.PIPE)


@pytest.mark.parametrize('orig,new,result', [
    (
        [{'sender': 1}, {'sender': 2}],
        [],
        set([])
    ),
    (
        [{'sender': 1}, {'sender': 2}],
        [{'sender': 1}, {'sender': 2}],
        set([])
    ),
    (
        [],
        [{'sender': 1}, {'sender': 2}],
        set([1, 2])
    ),
    (
        [{'sender': 1}],
        [{'sender': 1}, {'sender': 2}],
        set([2])
    ),
])
def test_compair_mco_ping_statuses(orig, new, result):
    assert result == mcollective.compair_mco_ping_statuses(orig, new)
