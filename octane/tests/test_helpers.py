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


DATA = [
    [{"Field": "id", "Value": 1}, {"Field": "name", "Value": "test"}],
    {"name": "test", "id": 2}
]

NORMALIZED_DATA = [
    {"name": "test", "id": 1},
    {"name": "test", "id": 2}
]


@pytest.mark.parametrize('data,normalized_data',
                         zip(DATA, NORMALIZED_DATA))
def test_normalized_cliff_show_json(data, normalized_data):
    res = helpers.normalized_cliff_show_json(data)
    assert res == normalized_data


@pytest.mark.parametrize(("source", "parameters_to_get", "parameters"), [
    ([
        (None, None, "option1", "value1"),
        (None, "section1", None, None),
        (None, "section1", None, None),
        (None, "section1", "option2", "value2"),
        (None, "section1", "option3", "value31"),
        (None, "section2", None, None),
        (None, "section2", "option4", "value4"),
        (None, "section2", "option3", "value32"),
        (None, "section3", "option3", "value33"),
    ], {
        "opt2": [("section1", "option2")],
        "opt3": [("section1", "option3"), ("section2", "option3")],
        "opt4": [("section1", "option4"), ("section2", "option4")],
    }, {
        "opt2": "value2",
        "opt3": "value32",
        "opt4": "value4",
    }),
])
def test_get_parameters(mocker, source, parameters_to_get, parameters):
    mock_fp = mock.Mock()
    mock_iter = mocker.patch("octane.util.helpers.iterate_parameters")
    mock_iter.return_value = source
    result = helpers.get_parameters(mock_fp, parameters_to_get)
    mock_iter.assert_called_once_with(mock_fp)
    assert result == parameters


@pytest.mark.parametrize("cmd_output, expected_result", [
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        | 85cfb077-3397-405e-ae61-dfce35d3073a | test_boot_volume_2 |
        +--------------------------------------+--------------------+""",
        [
            {
                "ID": "85cfb077-3397-405e-ae61-dfce35d3073a",
                "Name": "test_boot_volume_2",
            }
        ]
    ),
    (
        """
        +------+-------------+
        | ID   | Name        |
        +------+-------------+
        | id_1 | test_name_1 |
        | id_2 | test_name_2 |
        +------+-------------+
        """,
        [
            {
                "ID": "id_1",
                "Name": "test_name_1",
            },
            {
                "ID": "id_2",
                "Name": "test_name_2",
            }
        ]
    ),
    (
        """+--------------------------------------+--------------------+
        | ID                                   | Name               |
        +--------------------------------------+--------------------+
        +--------------------------------------+--------------------+""",
        []
    ),
])
def test_parse_table_output(cmd_output, expected_result):
    assert expected_result == helpers.parse_table_output(cmd_output)
