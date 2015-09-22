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

from octane.util import plugin


@pytest.mark.parametrize("installed,enabled", [
  (False, False),
  (True, False),
  (True, True),
])
def test_check_plugin(installed, enabled):
    settings = {'editable': {}}
    if installed:
        settings['editable']['emc_vnx'] = EMC_VNX_SETTINGS
        settings['editable']['emc_vnx']['metadata']['enabled'] = enabled
    assert plugin.is_installed(settings, 'emc_vnx') is installed
    assert plugin.is_enabled(settings, 'emc_vnx') is enabled


EMC_VNX_SETTINGS = {
    'emc_username': {
        'value': 'username',
    },
    'emc_pool_name': {
        'value': '',
    },
    'emc_sp_a_ip': {
        'value': '192.168.200.30',
    },
    'emc_sp_b_ip': {
        'value': '192.168.200.31',
    },
    'emc_password': {
        'value': 'password',
    },
    'metadata': {
        'enabled': 'false'
    }
}
