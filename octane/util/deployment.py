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

import logging
import os.path
import time
import yaml

from fuelclient.v1 import graph
from octane import magic_consts

LOG = logging.getLogger(__name__)


def graphs_upload(orig_id, seed_id):
    """Upload graphs to Nailgun with fuelclient.

    Read all yaml files from Octane deployment directory.
    Based on filename upload graph to original or seed environment.
    """
    client = graph.GraphClient()

    graph_path = os.path.join(magic_consts.DEPLOYMENT_DIR,
                              'puppet/octane_tasks/examples')

    for f in os.listdir(graph_path):
        if f.endswith(".yaml"):

            # Use filename as graph name
            graph_name = os.path.splitext(f)[0]

            # If name has "orig" upload graph to orig env
            # If name has "seed" upload graph to seed env
            # Else skip upload
            if "orig" in graph_name:
                env_id = orig_id
            elif "seed" in graph_name:
                env_id = seed_id
            else:
                continue

            # Read graph yaml file
            with open(os.path.join(graph_path, f), "r") as yaml_file:
                graph_data = yaml.load(yaml_file)
                if not graph_data:
                    continue

            # TODO: Handle exceptions
            client.upload(graph_data, "clusters", env_id, graph_name)


def graph_execute_and_wait(graph_type, env_id):
    """Execute graph with fuelclient and wait until finished."""
    client = graph.GraphClient()
    graph_task = client.execute(env_id, None, graph_type=graph_type)

    started_at = time.time()
    timeout = 1800
    check_freq = 30
    while True:
        status = graph_task.status

        # Return True if ready
        if status == 'ready':
            LOG.info("Graph '%s' for environment %s finished successfully."
                     % (graph_type, env_id))
            return True

        # Return False if error
        if status == 'error':
            LOG.error("Graph '%s' for environment %s finished with error."
                      % (graph_type, env_id))
            return False

        # Raise exception if timeout
        if time.time() - started_at >= timeout:
            raise Exception("Timeout waiting for graph '%s' execution."
                            % graph_type)

        LOG.info("Graph '%s' for environment %s has status '%s'"
                 % (graph_type, env_id, status))

        time.sleep(check_freq)


def graph_list(env_id):
    """Return list with graph names(types)."""
    client = graph.GraphClient()
    # TODO: Take into account not only cluster graphs
    return [g['relations'][0]['type'] for g in client.list(env_id)]
