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

import io
import json

import pytest

from octane.util import mcollective


@pytest.mark.parametrize("status", [
    {"a": "b", "c": "d"},
])
def test_get_mco_ping_status(mocker, status):
    stdout = io.BytesIO(json.dumps(status))
    mock_popen = mocker.patch("octane.util.subprocess.popen")
    mock_popen.return_value.__enter__.return_value.stdout = stdout
    result = mcollective.get_mco_ping_status()
    assert result == status


@pytest.mark.parametrize(("orig", "new", "offline"), [
    ([{"sender": 1}, {"sender": 2}], [{"sender": 1}], set([2])),
])
def test_compair_mco_ping_statuses(mocker, orig, new, offline):
    assert mcollective.compair_mco_ping_statuses(orig, new) == offline
