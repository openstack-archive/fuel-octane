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


@pytest.mark.parametrize(("args", "functional", "health", "requirements"), [
    (['--all'], True, True, True),
    ([], True, True, True),
    (['--functional'], True, False, False),
    (['--health'], False, True, False),
    (['--requirements'], False, False, True),
    (['--health', '--requirements'], False, True, True),
    (['--functional', '--health', '--requirements'], True, True, True),
    (['--functional', '--health'], True, True, False),
    (['--functional', '--requirements'], True, False, True),
])
@pytest.mark.parametrize(("params", "exception"), [
    ([], True),
    (['1'], True),
    (['1', '2'], False),
])
def test_upgrade_db_with_graph(
        mocker, octane_app,
        params, args, functional, health, requirements, exception):
    call_function = mocker.patch('octane.commands.check.check_runner')
    cmd = ['check'] + params + args
    if exception:
        with pytest.raises(Exception):
            octane_app.run(cmd)
        assert not call_function.called
    else:
        call_args = [int(i) for i in params] + [
            functional, health, requirements]
        octane_app.run(cmd)
        call_function.assert_called_once_with(*call_args)
