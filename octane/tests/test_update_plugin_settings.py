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

import mock
import pytest

from octane.commands import update_plugin_settings


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.update_plugin_settings'
                     '.transfer_plugins_settings')
    plugins_str = ','.join(update_plugin_settings.PLUGINS)
    octane_app.run(["update-plugin-settings", "--plugins", plugins_str,
                    "1", "2"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2, update_plugin_settings.PLUGINS.keys())


def test_transfer_plugin_settings(mocker):
    plugin = mock.Mock()
    mocker.patch.object(update_plugin_settings, 'PLUGINS', {'plugin': plugin})
    env_cls = mocker.patch('fuelclient.objects.environment.Environment')
    get_astute_yaml = mocker.patch('octane.util.env.get_astute_yaml')
    attrs = {'editable': {'plugin': {}}}
    env_cls.return_value.get_settings_data.return_value = attrs
    update_plugin_settings.transfer_plugins_settings(1, 2, ['plugin'])
    plugin.assert_called_once_with(get_astute_yaml.return_value, {})


def test_transfer_plugin_settings_fail(mocker):
    plugin = mock.Mock()
    mocker.patch.object(update_plugin_settings, 'PLUGINS', {'plugin': plugin})
    env_cls = mocker.patch('fuelclient.objects.environment.Environment')
    mocker.patch('octane.util.env.get_astute_yaml')
    attrs = {'editable': {'plugin1': {}}}
    env_cls.return_value.get_settings_data.return_value = attrs
    with pytest.raises(update_plugin_settings.PluginNotConfigured):
        update_plugin_settings.transfer_plugins_settings(1, 2, ['plugin'])
