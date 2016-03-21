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
import copy

from fuelclient import fuelclient_settings as settings


@contextlib.contextmanager
def set_auth_context(auth_context):
    settings.get_settings()
    config = settings._SETTINGS.config
    orig_config = copy.deepcopy(config)
    config["KEYSTONE_USER"] = auth_context.user
    config["KEYSTONE_PASS"] = auth_context.password
    yield
    config = orig_config
