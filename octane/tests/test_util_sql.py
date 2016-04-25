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

from octane.util import sql
from octane.util import subprocess


@pytest.mark.parametrize("sql_raw, result_data", [
    ("row_1|val_1\nrow_2|val_1\n", ["row_1|val_1", "row_2|val_1"]),
    ("", [])
])
@pytest.mark.parametrize("db", ["nailgun", "keystone"])
def test_run_sql(mocker, sql_raw, result_data, db):
    run_mock = mocker.patch(
        "octane.util.docker.run_in_container",
        return_value=(sql_raw, None))
    test_sql = "test_sql"
    results = sql.run_psql_in_container(test_sql, db)
    run_mock.assert_called_once_with(
        "postgres",
        [
            "sudo",
            "-u",
            "postgres",
            "psql",
            db,
            "--tuples-only",
            "--no-align",
            "-c",
            test_sql,
        ],
        stdout=subprocess.PIPE
    )
    assert result_data == results
