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
import time

from octane.util import subprocess

LOG = logging.getLogger(__name__)


def wait_for_service(service, attempts=120, delay=5):
    cmd = ['systemctl', '-p', 'ActiveState', 'show', service]
    for i in xrange(attempts):
        output = subprocess.call_output(cmd)
        lines = output.splitlines()
        _, _, state = lines[0].partition('=')
        if state == "active":
            LOG.info("Service %s is started", service)
            break
        elif state == "failed":
            LOG.error("Service %s failed to start, exiting", service)
            raise Exception("Service %s failed to start" % service)
        else:
            LOG.debug("Service %s is starting, waiting %s seconds",
                      service, delay)
            time.sleep(delay)
    else:
        raise Exception("Timeout waiting for service %s to start "
                        "after %d seconds" % (service, attempts * delay))
