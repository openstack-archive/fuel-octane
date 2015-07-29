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

from octane import app as o_app


def test_help():
    out, err = io.BytesIO(), io.BytesIO()
    app = o_app.OctaneApp(stdin=io.BytesIO(), stdout=out, stderr=err)
    try:
        app.run(["--help"])
    except SystemExit as e:
        assert e.code == 0
    assert not err.getvalue()
    assert 'Could not' not in out.getvalue()
