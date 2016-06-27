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

import mock
import pytest


from octane.util import docker


@pytest.mark.parametrize("container", ["container_name"])
@pytest.mark.parametrize("prefix", ["prefix_name"])
@pytest.mark.parametrize("patches", [["patch_1"], ["patch_1", "patch_2"]])
def test_applied_patches(mocker, container, prefix, patches):
    apply_patches = mocker.patch("octane.util.docker.apply_patches")
    with docker.applied_patches(container, prefix, *patches):
        pass
    assert [
        mock.call(container, prefix, *patches),
        mock.call(container, prefix, *patches, revert=True)
    ] == apply_patches.call_args_list
