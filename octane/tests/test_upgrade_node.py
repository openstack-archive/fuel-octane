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

import pytest


@pytest.mark.parametrize('live_migration', [True, False])
def test_parser(mocker, octane_app, live_migration):
    m = mocker.patch('octane.commands.upgrade_node.upgrade_node')
    cmd = ["upgrade-node", "--isolated", "1", "2", "3"]
    if not live_migration:
        cmd = cmd + ["--no-live-migration"]
    octane_app.run(cmd)
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(
        1, [2, 3],
        isolated=True, network_template=None, live_migration=live_migration)
