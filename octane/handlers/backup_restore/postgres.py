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
import logging
import requests
import six
import urlparse
import yaml

from keystoneclient.v2_0 import Client as keystoneclient

from octane.handlers.backup_restore import base
from octane import magic_consts
from octane.util import docker
from octane.util import helpers
from octane.util import subprocess


LOG = logging.getLogger(__name__)


class PostgresArchivatorMeta(type):

    def __init__(cls, name, bases, attr):
        super(PostgresArchivatorMeta, cls).__init__(name, bases, attr)
        cls.container = "postgres"
        if cls.db is not None and cls.cmd is None:
            cls.cmd = ["sudo", "-u", "postgres", "pg_dump", "-C", cls.db]
        if cls.db is not None and cls.filename is None:
            cls.filename = "postgres/{0}.sql".format(cls.db)


@six.add_metaclass(PostgresArchivatorMeta)
class PostgresArchivator(base.CmdArchivator):
    db = None

    def restore(self):
        dump = self.archive.extractfile(self.filename)
        subprocess.call([
            "systemctl", "stop", "docker-{0}.service".format(self.db)
        ])
        docker.stop_container(self.db)
        docker.run_in_container(
            "postgres",
            ["sudo", "-u", "postgres", "dropdb", "--if-exists", self.db],
        )
        with docker.in_container("postgres",
                                 ["sudo", "-u", "postgres", "psql"],
                                 stdin=subprocess.PIPE) as process:
            process.stdin.write(dump.read())
        subprocess.call([
            "systemctl", "start", "docker-{0}.service".format(self.db)
        ])
        docker.start_container(self.db)


class NailgunArchivator(PostgresArchivator):
    db = "nailgun"

    def __post_data_to_nailgun(self, url, data, user, password):
        ksclient = keystoneclient(
            auth_url=magic_consts.KEYSTONE_API_URL,
            username=user,
            password=password,
            tenant_name=magic_consts.KEYSTONE_TENANT_NAME,
        )
        resp = requests.post(
            urlparse.urljoin(magic_consts.NAILGUN_URL, url),
            json.dumps(data),
            headers={
                "X-Auth-Token": ksclient.auth_token,
                "Content-Type": "application/json",
            })
        LOG.debug(resp.content)
        return resp

    def post_restore_action(self):
        with open("/etc/fuel/astute.yaml") as astute_conf:
            data_dict = yaml.load(astute_conf.read())["FUEL_ACCESS"]
        user = data_dict["user"]
        password = data_dict["password"]
        data, _ = docker.run_in_container(
            "nailgun",
            ["cat", "/usr/share/fuel-openstack-metadata/openstack.yaml"],
            stdout=subprocess.PIPE)
        fixtures = yaml.load(data)
        base_release_fields = fixtures[0]['fields']
        for fixture in fixtures[1:]:
            release = helpers.merge_dicts(
                base_release_fields, fixture['fields'])
            self.__post_data_to_nailgun(
                "/api/v1/releases/", release, user, password)
        subprocess.call([
            "fuel",
            "release",
            "--sync-deployment-tasks",
            "--dir",
            "/etc/puppet/",
        ])


class KeystoneArchivator(PostgresArchivator):
    db = "keystone"
