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

from octane.util import env as env_util
from octane.util import ssh


class NovaRunner(object):

    def __init__(self, env):
        self.env = env

    @property
    def controller(self):
        return env_util.get_one_controller(self.env)

    @staticmethod
    def _generate_cmd(cmd):
        run_cmd = ['.', '/root/openrc;'] + cmd
        return ['sh', '-c', ' '.join(run_cmd)]

    def call(self, cmd, **kwargs):
        return ssh.call(
            self._generate_cmd(cmd), node=self.controller, **kwargs)

    def call_output(self, cmd, **kwargs):
        return ssh.call_output(
            self._generate_cmd(cmd), node=self.controller, **kwargs)
