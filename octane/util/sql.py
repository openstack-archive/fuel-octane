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

from octane.util import docker
from octane.util import subprocess


def run_sql_on_container(sql, container, db):
    sql_run_prams = [
        "sudo", "-u", "postgres", "psql", db, "--tuples-only", "-c",
    ]
    results, _ = docker.run_in_container(
        container,
        sql_run_prams + [sql],
        stdout=subprocess.PIPE)
    return results.strip().splitlines()
