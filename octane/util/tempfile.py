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

from __future__ import absolute_import

import contextlib
import os
import shutil
import tempfile


def get_tempname(dir=None, prefix=None):
    kwargs = {}
    if prefix is not None:
        kwargs["prefix"] = prefix
    fd, tmp_file_name = tempfile.mkstemp(dir=dir, **kwargs)
    os.close(fd)
    return tmp_file_name


@contextlib.contextmanager
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)
