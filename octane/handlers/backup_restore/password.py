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

import hashlib
import io
import tarfile

from octane.handlers.backup_restore import base
from octane.util import encryption


class PasswordArchivator(base.Base):

    name = "encryption/check"

    def backup(self):
        if not self.password:
            return
        data = encryption.encrypt(hashlib.sha256(self.password).hexdigest(),
                                  self.password)
        info = tarfile.TarInfo(self.name)
        info.size = len(data)
        tar_io = io.BytesIO()
        tar_io.write(data)
        tar_io.seek(0)
        self.archive.addfile(info, tar_io)

    def pre_restore_check(self):
        if self.name not in self.archive and not self.password:
            return
        if self.name in self.archive and not self.password:
            raise Exception("password required")
        if self.name not in self.archive and self.password:
            raise Exception("Password not needed")
        data = self.archive.extractfile(self.name).read()
        pswd_hash = hashlib.sha256(self.password).hexdigest()
        if encryption.decrypt(data, self.passwrod) != pswd_hash:
            raise Exception("Password not match")
