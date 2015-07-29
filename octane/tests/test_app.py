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

import io

import pytest

from octane import app as o_app


@pytest.fixture
def octane_app():
    return o_app.OctaneApp(stdin=io.BytesIO(), stdout=io.BytesIO(),
                           stderr=io.BytesIO())


def test_help(octane_app):
    try:
        octane_app.run(["--help"])
    except SystemExit as e:
        assert e.code == 0
    assert not octane_app.stderr.getvalue()
    assert 'Could not' not in octane_app.stdout.getvalue()
