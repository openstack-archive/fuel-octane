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

import json
import os
import urlparse
import yaml

from octane.handlers.backup_restore import base

from octane.util import docker
from octane.util import subprocess


class NaigunWWWBackup(base.PathArchivator):
    path = "/var/www/nailgun/"
    db = "nailgun"
    name = None
    sql = None

    def _get_values_list(self, data):
        raise NotImplementedError("No values")

    def backup(self):
        with open("/etc/fuel/astute.yaml", "r") as current:
            current_yaml = yaml.load(current)
            ipaddr = current_yaml["ADMIN_NETWORK"]["ipaddress"]
        with docker.in_container(
                "postgres",
                [
                    "sudo",
                    "-u",
                    "postgres",
                    "psql",
                    self.db,
                    "--tuples-only",
                    "--record-separator-zero",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE) as psql_runner:
            psql_runner.stdin.write(self.sql)
            results, _ = psql_runner.communicate()
            results = results.strip().split("\n")
        already_backuped = set()
        for line in results:
            data = json.loads(line)
            for value in self._get_values_list(data):
                if ipaddr in value['uri']:
                    path = urlparse.urlsplit(value['uri']).path
                    dir_name = path.lstrip("/").split('/', 1)[0]
                    if dir_name in already_backuped:
                        continue
                    already_backuped.add(dir_name)
                    path = os.path.join(self.path, dir_name)
                    self.archive.add(path, self.name)


class MirrorsBackup(NaigunWWWBackup):

    name = "mirrors"
    sql = "select editable from attributes;"

    def _get_values_list(self, data):
        return data['repo_setup']['repos']['value']


class RepoBackup(NaigunWWWBackup):

    name = "repos"
    sql = "select generated from attributes;"

    def _get_values_list(self, data):
        return data['provision']['image_data'].values()
