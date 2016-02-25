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


def is_installed(env, plugin_name):
    settings = env.get_settings_data()
    if plugin_name in settings['editable']:
        return True
    return False


def is_enabled(env, plugin_name):
    settings = env.get_settings_data()
    if plugin_name not in settings['editable']:
        return False
    return settings['editable'][plugin_name]['metadata']['enabled']


def is_contrail_plugin_enabled(env):
    return is_enabled(env, 'contrail')
