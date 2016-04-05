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

from octane.handlers.backup_restore import base
from octane.util import archivate
from octane.util import cobbler
from octane.util import service
from octane.util import subprocess


class CobblerArchivator(base.PathArchivator):
    path = '/var/lib/cobbler/config/systems.d/'
    name = 'cobbler'

    def restore(self):
        for member in archivate.filter_members(self.archive, self.name):
            fp_member = self.archive.extractfile(member)
            data = json.load(fp_member)
            # NOTE(akscram): There two profiles in 8.0, such as
            # 'bootstrap' and 'ubuntu_bootstrap', but in 9.0 only
            # 'ubuntu_bootstrap' is used.
            if data['profile'] == 'bootstrap':
                data['profile'] = 'ubuntu_bootstrap'
            _, _, filename = member.name.partition(os.path.sep)
            path = os.path.join(self.path, filename)
            with open(path, 'wb') as fp:
                json.dump(data, fp)
            os.chmod(path, member.mode)
        subprocess.call(['systemctl', 'restart', 'cobblerd.service'])
        service.wait_for_service('cobblerd.service', attempts=24)
        cobbler.wait_for_sync(attempts=24)
