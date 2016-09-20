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
import requests

from octane.util import auth


@pytest.mark.parametrize("status,valid", [
    (401, False),
    (500, requests.HTTPError),
    (200, True),
])
def test_is_creds_valid(mocker, status, valid):
    mock_resp = mock.Mock(spec=["status_code", "raise_for_status"])
    mock_resp.status_code = status

    mocker.patch("fuelclient.client.APIClient.get_request_raw",
                 return_value=mock_resp)

    if not isinstance(valid, bool):
        mock_resp.raise_for_status.side_effect = valid()
        with pytest.raises(valid):
            auth.is_creds_valid('a', 'b')
    else:
        assert auth.is_creds_valid('a', 'b') == valid
        if not valid:
            assert not mock_resp.raise_for_status.called
