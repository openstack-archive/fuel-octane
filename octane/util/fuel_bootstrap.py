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

import re

from octane.util import subprocess


def get_images_uuids():
    # TODO(vegasq) how to exclude active images?
    uuid_regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    return set(re.findall(uuid_regex,
                          subprocess.call_output(["fuel-bootstrap", "list"])))


def delete_image(uuid):
    try:
        subprocess.call(["fuel-bootstrap", "delete", uuid])
    except subprocess.CalledProcessError:
        # Ignore active images
        pass
