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

import contextlib

from octane.util import docker
from octane.util import subprocess


def patch_apply(cwd, patches, revert=False):
    for path in patches:
        with open(path, 'rb') as patch:
            try:
                subprocess.call(["patch", "-R", "-p1"], stdin=patch, cwd=cwd)
            except subprocess.CalledProcessError:
                if not revert:
                    pass
                else:
                    raise
            if not revert:
                patch.seek(0)
                subprocess.call(["patch", "-N", "-p1"], stdin=patch, cwd=cwd)


@contextlib.contextmanager
def patch_container_service(container, service, prefix, *patches):
    try:
        with docker.applied_patches(container, prefix, *patches) as val:
            docker.run_in_container(container, ["service", service, "restart"])
            yield
    finally:
        docker.run_in_container(container, ["service", service, "restart"])
