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


def test_prepare_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.prepare.prepare')
    octane_app.run(["prepare"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with()


def test_revert_parser(mocker, octane_app):
    mock_puppet = mocker.patch('octane.commands.prepare.patch_puppet')
    mock_apply = mocker.patch('octane.commands.prepare.apply_patches')
    octane_app.run(["revert-prepare"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    mock_apply.assert_called_once_with(revert=True)
    mock_puppet.assert_called_once_with(revert=True)
