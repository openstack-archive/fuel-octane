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

import functools
import logging

import stevedore

LOG = logging.getLogger(__name__)


class _GetNodesHandlersFactory(object):
    def __init__(self, name):
        self.name = name

    def on_load_failure_callback(self, manager, endpoint, exc):
        LOG.error('Failed to load %s: %s', endpoint.name, exc)
        raise  # Avoid unexpectedly skipped steps

    @property
    def extensions(self):
        extension_manager = stevedore.ExtensionManager(
            'octane.handlers.' + self.name,
            on_load_failure_callback=self.on_load_failure_callback,
        )
        extensions = dict(extension_manager.map(
            lambda ext: (ext.name, ext.plugin)))
        self.__dict__['extensions'] = extensions
        return extensions

    def __call__(self, nodes, *args, **kwargs):
        handlers = []
        for node in nodes:
            for role in node.data['roles']:
                try:
                    cls = self.extensions[role]
                except KeyError:
                    raise Exception("Role '%s' of node #%s is not supported" %
                                    (role, node.data['id']))
                else:
                    handlers.append(cls(node, *args, **kwargs))
        return functools.partial(self.call_method_on_all, handlers)

    @staticmethod
    def call_method_on_all(handlers, method):
        result = dict()
        for handler in handlers:
            try:
                result = list()
                result.append(getattr(handler, method)())
            except NotImplementedError:
                LOG.info("Method '%s' not implemented in handler %s",
                         method, type(handler).__name__)
        return result
