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

from octane.util import fuel_bootstrap


def test_get_images_uuids(mocker):
    fake_output = [{"status": "active",
                    "uuid": "00000000-1111-2222-3333-444444444444",
                    "label": "00000000-1111-2222-3333-444444444444"},
                   {"status": "",
                    "uuid": "55555555-6666-7777-8888-999999999999",
                    "label": "55555555-6666-7777-8888-999999999999"}]

    mocker.patch('octane.util.subprocess.call_output',
                 return_value=json.dumps(fake_output))

    uuids = fuel_bootstrap.get_not_active_images_uuids()

    assert uuids == [fake_output[1]['uuid']]


def test_delete_image(mocker):
    fake_uuid = "00000000-1111-2222-3333-444444444444"
    call = mocker.patch('octane.util.subprocess.call')
    fuel_bootstrap.delete_image(fake_uuid)
    call.assert_called_once_with(['fuel-bootstrap', 'delete', fake_uuid])
