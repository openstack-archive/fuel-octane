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

from contextlib import contextmanager
from octane.util import subprocess


LOG = logging.getLogger(__name__)
TIMEOUT_FILE = "/etc/systemd/user.conf.d/99-octane-timeout.conf"
TIMEOUT_CONF = ("[Service]\n"
                "TimeoutStartSec={0}\n")


@contextmanager
def set_systemctl_start_timeout(timeout):
    confdir = os.path.dirname(TIMEOUT_FILE)
    if not os.path.isdir(confdir):
        os.mkdirs(confdir)
    with open(os.path.join(TIMEOUT_FILE), 'w') as f:
        f.write(TIMEOUT_CONF.format(timeout))
    LOG.info("Set timeout for systemd service start to %s", timeout)
    try:
        yield
    finally:
        os.unlink(TIMEOUT_FILE)
        LOG.info("Unset systemd timeout override for service start")


def _container_action(service, action):
    subprocess.call(["systemctl",
                     action,
                     "docker-{0}.service".format(service)])


def stop_container(service):
    _container_action(service, "stop")
    LOG.info("Container for service %s stopped", service)


def start_container(service):
    _container_action(service, "start")
    LOG.info("Container for service %s started", service)
