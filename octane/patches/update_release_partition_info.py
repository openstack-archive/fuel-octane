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

from nailgun.db import db
from nailgun.db.sqlalchemy import models

releases = db().query(models.Release)
for rel in releases:
    meta = rel.volumes_metadata
    for volume in meta['volumes']:
        if volume['min_size']['generator'] == 'calc_min_log_size':
            volume['min_size']['generator'] = 'calc_gb_to_mb'
            volume['min_size']['generator_args'] = [2]
    db().query(models.Release).filter_by(id=rel.id).update(
        {"volumes_metadata": meta})

db().commit()
