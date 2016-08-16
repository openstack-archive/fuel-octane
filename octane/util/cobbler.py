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

from octane.util import helpers
from octane.util import subprocess


def get_default_profile():
    astute = helpers.get_astute_dict()
    default_profile = astute.get("bootstrap_profile", "ubuntu_bootstrap")
    return default_profile


def profile_exists(name):
    out = subprocess.call_output(
        ["cobbler", "profile", "find", "--name", name])
    return bool(out.strip())


def profile_copy(name, new_name):
    subprocess.call(["cobbler", "profile", "copy",
                     "--name", name, "--newname", new_name])


def systems_edit_profile(profile_name, new_profile_name):
    out = subprocess.call_output(
        ["cobbler", "system", "find", "--profile", profile_name])
    system_names = out.strip().split()
    for system_name in system_names:
        subprocess.call(["cobbler", "system", "edit",
                         "--name", system_name, "--profile", new_profile_name])


def profile_remove(name):
    if profile_exists(name):
        subprocess.call(["cobbler", "profile", "remove", "--name", name])


@contextlib.contextmanager
def rename_bootstrap_profile_for_systems():
    default_profile = get_default_profile()
    bootstrap_exists = profile_exists("bootstrap")
    if not bootstrap_exists:
        profile_copy(default_profile, "bootstrap")
    yield
    systems_edit_profile("bootstrap", default_profile)
    if not bootstrap_exists:
        profile_remove("bootstrap")
