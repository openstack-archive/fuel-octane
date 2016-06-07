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


def get_files_from_patch(patch):
    """Get all files touched by a patch"""
    result = []
    with open(patch) as p:
        for line in p:
            if line.startswith('+++'):
                fname = line[4:].strip()
                if fname.startswith('b/'):
                    fname = fname[2:]
                tab_pos = fname.find('\t')
                if tab_pos > 0:
                    fname = fname[:tab_pos]
                result.append(fname)
    return result


def get_filenames_from_patches(prefix, *patches):
    files = []
    for patch in patches:
        for fname in get_files_from_patch(patch):
            if fname.startswith(prefix):
                files.append(fname[len(prefix) + 1:])
            else:
                files.append(fname)
    return files
