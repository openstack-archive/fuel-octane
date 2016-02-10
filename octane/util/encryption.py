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

from cliff import command
import contextlib
import getpass
import os

from octane.util import subprocess


@contextlib.contextmanager
def _work_on_io(action, password, input_io=None, output_io=None):
    r_fd, w_fd = os.pipe()
    cmd = ["gpg",
           "--passphrase-fd",
           str(r_fd),
           "--batch",
           action,
           "--output",
           "-"]
    with subprocess.popen(
            cmd,
            stdin=input_io or subprocess.PIPE,
            stdout=output_io or subprocess.PIPE,
            close_fds=False) as process:
        os.close(r_fd)
        pswd_input = os.fdopen(w_fd, "w")
        pswd_input.write("{0}\n".format(password))
        pswd_input.close()
        yield process.stdin, process.stdout


@contextlib.contextmanager
def encrypt_io(password, input_io=None, output_io=None):
    with _work_on_io("--symmetric", password, input_io, output_io) as res:
        yield res


@contextlib.contextmanager
def decrypt_io(password, input_io=None, output_io=None):
    with _work_on_io("--decrypt", password, input_io, output_io) as res:
        yield res


class EncryptCommandMixin(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super(EncryptCommandMixin, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--password",
            type=str,
            dest="password",
            help="Backup password")
        enc_group = parser.add_mutually_exclusive_group()
        enc_group.add_argument(
            '--encrypted',
            dest='encrypted',
            action='store_true')
        enc_group.add_argument(
            '--not-encrypted',
            dest='encrypted',
            action='store_false')
        enc_group.set_defaults(encrypted=True)
        return parser

    def take_action(self, parsed_args):
        super(EncryptCommandMixin, self).take_action(parsed_args)
        password = None
        if parsed_args.encrypted:
            password = parsed_args.password or getpass.getpass()
            if not password:
                raise Exception("Password required for encrypted backup")
        elif getattr(parsed_args, "password", None):
            raise Exception("Password not required for not encrypted backup")
        parsed_args.password = password
