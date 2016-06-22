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

from octane import handlers


class UpgradeHandler(object):
    def __init__(self, node, env, isolated, live_migration):
        self.node = node
        self.orig_env = self.node.env
        self.orig_version = self.orig_env.data["fuel_version"]
        self.env = env
        self.isolated = isolated
        self.live_migration = live_migration

    def preupgrade(self):
        raise NotImplementedError('preupgrade')

    def prepare(self):
        raise NotImplementedError('prepare')

    def predeploy(self):
        raise NotImplementedError('predeploy')

    def postdeploy(self):
        raise NotImplementedError('postdeploy')

get_nodes_handlers = handlers._GetNodesHandlersFactory('upgrade')
