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

from octane.handlers.backup_restore import astute
from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import fuel_uuid
from octane.handlers.backup_restore import postgres
from octane.handlers.backup_restore import puppet
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version


MANAGERS = [
    astute.AstuteArchivator,
    fuel_keys.FuelKeysArchivator,
    fuel_uuid.FuelUUIDArchivator,
    cobbler.CobblerArchivator,
    postgres.KeystoneArchivator,
    postgres.NailgunArchivator,
    puppet.PuppetArchivator,
    ssh.SshArchivator,
    version.VersionArchivator,
]
