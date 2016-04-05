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


def wait_for_sync(attempts=120, delay=5):
    for i in xrange(attempts):
        try:
            subprocess.call(['cobbler', 'sync'])
        except subprocess.CalledProcessError as err:
            if err.returncode == 155:
                LOG.debug("Cobbler service is not yet ready, waiting %s "
                          "seconds", delay)
                time.sleep(delay)
            else:
                LOG.error("Cobbler synchronization failed, exiting")
                raise Exception("Cobbler synchronization failed")
        else:
            LOG.info("Cobbler synchronization finished")
            break
