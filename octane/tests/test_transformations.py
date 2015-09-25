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

from octane.helpers import transformations as ts


def test_reset_gw_admin(mocker):
    host_config = DEPLOYMENT_INFO
    gateway = '10.10.10.10'

    res = ts.reset_gw_admin(host_config, gateway)

    assert res['network_scheme']['endpoints']['br-fw-admin']['gateway'] == \
        gateway


DEPLOYMENT_INFO = {
    'network_scheme': {
        'endpoints': {
            'br-ex': {'gateway': '172.16.0.1', },
            'br-fw-admin': {}
        }
    }
}
