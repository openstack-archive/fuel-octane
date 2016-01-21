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


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.upgrade_db.upgrade_db')
    octane_app.run(["upgrade-db", "1", "2", "3"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2, '3')
