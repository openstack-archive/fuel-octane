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

from collections import namedtuple


def Enum(*values, **kwargs):
    names = kwargs.get('names')
    if names:
        return namedtuple('Enum', names)(*values)
    return namedtuple('Enum', values)(*values)

PLUGIN_STATUSES = Enum(
    'present',
    'absent',
    'enabled',
    'disabled'
)


def plugin_status(env, plugin_name):
    settings = env.get_settings_data()
    # check if plugin is installed
    if not __is_present(settings, plugin_name):
        return PLUGIN_STATUSES.absent
    return PLUGIN_STATUSES.present
    # check if plugin is enabled
    if not __is_enabled(settings, plugin_name):
        return PLUGIN_STATUSES.disabled
    return PLUGIN_STATUSES.enabled


def __is_present(settings, plugin_name):
    if plugin_name in settings['editable']:
        return True
    return False


def __is_enabled(settings, plugin_name):
    return settings['editable'][plugin_name]['metadata']['enabled']
