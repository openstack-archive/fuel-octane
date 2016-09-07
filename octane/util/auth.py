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

from collections import namedtuple
from fuelclient.client import APIClient

from octane.util import fuel_client


Context = namedtuple('Context', ('user', 'password'))


def is_creds_valid(user, password):
    with fuel_client.set_auth_context(Context(user, password)):
        resp = APIClient.get_request_raw('/clusters')
        if resp.status_code != 401:
            resp.raise_for_status()
            return True
        return False
