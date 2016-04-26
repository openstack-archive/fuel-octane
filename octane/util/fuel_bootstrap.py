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

from octane.util import subprocess


def get_not_active_images_uuids():
    fuel_bootstrap_list = ["fuel-bootstrap", "list", "--format", "json"]
    images = json.loads(subprocess.call_output(fuel_bootstrap_list))
    return [img["uuid"] for img in images if img["status"] != "active"]


def delete_image(uuid):
    subprocess.call(["fuel-bootstrap", "delete", uuid])
