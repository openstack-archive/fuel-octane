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


def test_get_astute_dict(mocker):
    mock_load = mocker.patch("octane.util.helpers.load_yaml")
    data = helpers.get_astute_dict()
    mock_load.assert_called_once_with("/etc/fuel/astute.yaml")
    assert data is mock_load.return_value


@pytest.mark.parametrize(("source", "parameters"), [
    ([
        "option1 =  value1\n",
        "[section1]\n",
        "# some comment\n",
        "option2= value2\n",
        "[section2]\n",
        " option3  =value3  \n",
    ], [
        (None, "option1", "value1"),
        ("section1", None, None),
        ("section1", None, None),
        ("section1", "option2", "value2"),
        ("section2", None, None),
        ("section2", "option3", "value3"),
    ]),
])
def test_iterate_parameters(source, parameters):
    expected_result = []
    for line, params in zip(source, parameters):
        expected_result.append((line,) + params)
    result = list(helpers.iterate_parameters(source))
    assert result == expected_result
