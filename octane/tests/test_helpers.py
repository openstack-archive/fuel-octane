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

from octane.util import helpers


@pytest.mark.parametrize("base, update, result", [
    ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
    ({"a": 1, "b": 3}, {"b": 2}, {"a": 1, "b": 2}),
    (
        {"a": 1, "b": {"a": 1}},
        {"b": {"a": 2, "b": 3}},
        {"a": 1, "b": {"a": 2, "b": 3}},
    ),
    (
        {"a": 1, "b": {"a": 1}},
        {"b": {"b": 3}},
        {"a": 1, "b": {"a": 1, "b": 3}},
    ),
    (
        {"a": 1, "b": {"a": {"a": 1}}},
        {"b": {"a": {"b": 2}, "b": 3}},
        {"a": 1, "b": {"a": {"a": 1, "b": 2}, "b": 3}},
    ),
])
def test_merge_dicts(mocker, base, update, result):
    assert result == helpers.merge_dicts(base, update)
