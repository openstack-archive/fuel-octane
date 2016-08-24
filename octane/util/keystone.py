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


def unset_default_domain_id(filename):
    with subprocess.update_file(filename) as (old, new):
        for line, section, parameter, value in helpers.iterate_parameters(old):
            if section == "identity" and parameter == "default_domain_id":
                line = "#{0}".format(line)
            new.write(line)


@contextlib.contextmanager
def admin_token_auth(filename, pipelines):
    add_admin_token_auth(filename, pipelines)
    yield
    remove_admin_token_auth(filename, pipelines)
    subprocess.call(["systemctl", "restart", "openstack-keystone"])


def add_admin_token_auth(filename, pipelines):
    with replace_pipeline_items(filename, pipelines) as pipeline_items:
        for items in pipeline_items:
            if "admin_token_auth" in items:
                continue
            token_auth_idx = items.index("token_auth")
            items.insert(token_auth_idx, "admin_token_auth")


def remove_admin_token_auth(filename, pipelines):
    with replace_pipeline_items(filename, pipelines) as pipeline_items:
        for items in pipeline_items:
            if "admin_token_auth" in items:
                items.remove("admin_token_auth")


@contextlib.contextmanager
def replace_pipeline_items(filename, pipelines):
    def iterate_pipeline_items(old, new):
        for line, section, parameter, value in helpers.iterate_parameters(old):
            if section in pipelines and parameter == "pipeline":
                items = value.split()
                yield items
                new_value = " ".join(items)
                line = "{0} = {1}\n".format(parameter, new_value)
            new.write(line)

    with subprocess.update_file(filename) as (old, new):
        yield iterate_pipeline_items(old, new)
