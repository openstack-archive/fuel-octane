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

import shutil
import six

from octane.handlers.backup_restore import base
from octane import magic_consts
from octane.util import auth
from octane.util import patch
from octane.util import puppet
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
        with auth.set_astute_password(self.context):
            puppet.apply_task(self.db)


class NailgunArchivator(PostgresArchivator):
    db = "nailgun"
    services = [
        "nailgun",
        "oswl_flavor_collectord",
        "oswl_image_collectord",
        "oswl_keystone_user_collectord",
        "oswl_tenant_collectord",
        "oswl_vm_collectord",
        "oswl_volume_collectord",
        "receiverd",
        "statsenderd",
        "assassind",
    ]
    patches = magic_consts.NAILGUN_ARCHIVATOR_PATCHES

    def restore(self):
        with patch.applied_patch(*self.patches):
            super(NailgunArchivator, self).restore()


class KeystoneArchivator(PostgresArchivator):
    db = "keystone"
    services = ["openstack-keystone"]


class DatabasesArchivator(base.CollectionArchivator):
    archivators_classes = [
        KeystoneArchivator,
        NailgunArchivator,
    ]

    def restore(self):
        puppet.apply_task("postgresql")
        super(DatabasesArchivator, self).restore()
