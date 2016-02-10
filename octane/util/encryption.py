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

import os

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
            cmd, stdin=input_io, stdout=output_io,
            close_fds=False) as process:
        os.close(r_fd)
        pswd_input = os.fdopen(w_fd, "w")
        pswd_input.write("{0}\n".format(password))
        pswd_input.close()
        process.communicate()


def encrypt_io(input_io, output_io, password):
    _work_on_io(input_io, output_io, password, "--symmetric")


def decrypt_io(input_io, output_io, password):
    _work_on_io(input_io, output_io, password, "--decrypt")
