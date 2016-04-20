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

from octane.handlers.backup_restore import base


@pytest.mark.parametrize("action", ["backup", "restore", "pre_restore_check"])
@pytest.mark.parametrize("archivators", [[mock.Mock(), mock.Mock()], ])
def test_collection_archivator(action, archivators):

    class TestCollectionArchivator(base.CollectionArchivator):

        archivators_classes = archivators

    archive = mock.Mock()
    context = mock.Mock()

    getattr(TestCollectionArchivator(archive, context), action)()

    for archivator in archivators:
        getattr(archivator.return_value, action).assert_called_once_with()
