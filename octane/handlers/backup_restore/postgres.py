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
import shutil
import six

from octane.handlers.backup_restore import base
from octane import magic_consts
from octane.util import patch
from octane.util import puppet
from octane.util import sql
from octane.util import subprocess


class PostgresArchivatorMeta(type):

    def __init__(cls, name, bases, attr):
        super(PostgresArchivatorMeta, cls).__init__(name, bases, attr)
        if cls.db is not None and cls.cmd is None:
            cls.cmd = ["sudo", "-u", "postgres", "pg_dump", "-C", cls.db]
        if cls.db is not None and cls.filename is None:
            cls.filename = "postgres/{0}.sql".format(cls.db)


@six.add_metaclass(PostgresArchivatorMeta)
class PostgresArchivator(base.CmdArchivator):
    db = None
    services = []

    def restore(self):
        dump = self.archive.extractfile(self.filename)
        subprocess.call(["systemctl", "stop"] + self.services)
        subprocess.call(["sudo", "-u", "postgres", "dropdb", "--if-exists",
                         self.db])
        with subprocess.popen(["sudo", "-u", "postgres", "psql"],
                              stdin=subprocess.PIPE) as process:
            shutil.copyfileobj(dump, process.stdin)
        puppet.apply_task(self.db)


class NailgunArchivator(PostgresArchivator):
    db = "nailgun"
    services = [
        "nailgun.service",
        "oswl_flavor_collectord.service",
        "oswl_image_collectord.service",
        "oswl_keystone_user_collectord.service",
        "oswl_tenant_collectord.service",
        "oswl_vm_collectord.service",
        "oswl_volume_collectord.service",
        "receiverd.service",
        "statsenderd.service",
        "assassind.service",
    ]
    patches = magic_consts.NAILGUN_ARCHIVATOR_PATCHES

    def restore(self):
        for args in self.patches:
            patch.patch_apply(*args)
        try:
            super(NailgunArchivator, self).restore()
            self._repair_database_consistency()
        finally:
            for args in self.patches:
                patch.patch_apply(*args, revert=True)

    def _repair_database_consistency(self):
        values = []
        for line in sql.run_psql(
                "select id, generated from attributes;", self.db):
            c_id, c_data = line.split("|", 1)
            data = json.loads(c_data)
            data["deployed_before"] = {"value": True}
            values.append("({0}, '{1}')".format(c_id, json.dumps(data)))

        if values:
            sql.run_psql(
                'update attributes as a set generated = b.generated '
                'from (values {0}) as b(id, generated) '
                'where a.id = b.id;'.format(','.join(values)),
                self.db)


class KeystoneArchivator(PostgresArchivator):
    db = "keystone"
    services = ["openstack-keystone.service"]
