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

from octane.commands.update_plugin_settings import PLUGINS


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.update_plugin_settings'
                     '.transfer_plugins_settings')
    plugins_str = ','.join(PLUGINS)
    octane_app.run(["update-plugin-settings", "--plugins", plugins_str,
                    "1", "2"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2, PLUGINS.keys())
