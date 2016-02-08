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

import pytest

from octane.util import puppet as puppet_util
from octane.util import subprocess


def test_apply_host(mock_subprocess):
    puppet_util.apply_host()
    assert mock_subprocess.call_count == 1


def test_apply_host_error(mock_subprocess):
    exc = subprocess.CalledProcessError(1, 'TEST_PROCESS')
    mock_subprocess.side_effect = exc
    with pytest.raises(type(exc)):
        puppet_util.apply_host()
