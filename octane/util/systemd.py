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

from octane.util import subprocess


LOG = logging.getLogger(__name__)
SYSTEMD_DIR = "/etc/systemd/user.conf.d"
CONTENT = ("[Service]\n"
           "TimeoutStartSec={0}\n")


def set_systemctl_start_timeout(timeout):
    confdir = SYSTEMD_DIR
    if not os.path.isdir(confdir):
        os.mkdir(confdir)
    with open(os.path.join(confdir, "timeout.conf"), 'w') as f:
        f.write(CONTENT.format(timeout))
    LOG.info("Set timeout for systemd service start to %s",
             timeout)


def unset_systemctl_start_timeout():
    path = os.path.join(SYSTEMD_DIR,
                        "timeout.conf")
    if os.path.exists(path):
        try:
            os.unlink(path)
        except OSError as exc:
            LOG.error("Cannot delete file %s: %s",
                      path, exc.message)
        else:
            LOG.info("Unset systemd timeout override "
                     "for service start")


def _service_action(service, action):
    subprocess.call(["systemctl",
                     action,
                     "docker-{0}.service".format(service)])


def stop_service(service):
    _service_action(service, "stop")
    LOG.info("Service %s stopped", service)


def start_service(service):
    _service_action(service, "start")
    LOG.info("Service %s started", service)
