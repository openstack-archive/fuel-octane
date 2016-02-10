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

import io
import os
import tarfile

from octane.util import subprocess


def _work_on_io(input_io, output_io, password, action):
    r_fd, w_fd = os.pipe()
    cmd = ["gpg",
           "--passphrase-fd",
           str(r_fd),
           "--batch",
           action,
           "--output",
           "-"]
    with subprocess.popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            close_fds=False) as process:
        os.close(r_fd)
        pswd_input = os.fdopen(w_fd, "w")
        pswd_input.write("{0}\n".format(password))
        pswd_input.close()
        process.stdin.write(input_io.read())
        stdout, _ = process.communicate()
        output_io.write(stdout)


def encrypt_io(input_io, output_io, password):
    _work_on_io(input_io, output_io, password, "--symmetric")


def decrypt_io(input_io, output_io, password):
    _work_on_io(input_io, output_io, password, "--decrypt")


def _work_on_str(data, password, action):
    input_io = io.BytesIO()
    input_io.write(data)
    input_io.seek(0)
    output_io = io.BytesIO()
    action(input_io, output_io, password)
    output_io.seek(0)
    return output_io.read()


def encrypt(data, password):
    return _work_on_str(data, password, encrypt_io)


def decrypt(data, password):
    return _work_on_str(data, password, decrypt_io)


class EncryptedTarFile(tarfile.TarFile):

    def set_password(self, password):
        self.password = password

    def addfile(self, tarinfo, fileobj=None, *args, **kwargs):
        if fileobj:
            encr = io.BytesIO()
            encrypt_io(fileobj, encr, self.password)
            tarinfo.size = encr.__sizeof__()
            encr.seek(0)
        else:
            encr = None
        return super(EncryptedTarFile, self).addfile(
            tarinfo, encr, *args, **kwargs)

    def extractfile(self, member, *args, **kwargs):
        extracted_file = super(EncryptedTarFile, self).extractfile(
            member, *args, **kwargs)
        if not extracted_file:
            return extracted_file
        decrypted_io = io.BytesIO()
        decrypt_io(extracted_file, decrypted_io, self.password)
        return decrypt_io
