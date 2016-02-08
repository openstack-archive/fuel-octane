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

import logging
import os
import os.path

from octane import magic_consts


LOG = logging.getLogger(__name__)
CONTENT = ("[Service]\n"
           "TimeoutStartSec={0}\n")


def set_service_timeout(service, timeout):
    service_path = os.path.join(magic_consts.SYSTEMD_DIR,
                                "user.conf.d")
    try:
        os.mkdir(service_path)
    except OSError:
        pass
    with open(os.path.join(service_path, "timeout.conf"), 'w') as f:
        f.write(CONTENT.format(timeout))


def unset_service_timeout(service):
    path = os.path.join(magic_consts.SYSTEMD_DIR,
                        "user.conf.d",
                        "timeout.conf")
    try:
        os.unlink(path)
    except OSError as exc:
        LOG.info("Cannot delete file %s: %s",
                 path, exc.message)
