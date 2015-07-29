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

import sys

from cliff import app
from cliff import commandmanager as cm

import octane
from octane import log


class OctaneApp(app.App):
    def __init__(self, **kwargs):
        super(OctaneApp, self).__init__(
            description='Octane - upgrade your Fuel',
            version=octane.__version__,
            command_manager=cm.CommandManager('octane'),
            **kwargs
        )

    def configure_logging(self):
        super(OctaneApp, self).configure_logging()
        if self.options.verbose_level > 1:
            log.set_console_formatter(
                fmt='%(asctime)s %(levelname)-8s %(name)-15s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
            log.silence_iso8601()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    return OctaneApp().run(argv)
