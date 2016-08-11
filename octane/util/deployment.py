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

from fuelclient.v1 import graph
from octane import magic_consts
from octane.util import helpers

LOG = logging.getLogger(__name__)


def graph_upload_to_env(graph_file_path, env_id):
    """Upload graph file to Nailgun for environment."""
    # Try to download graph data
    graph_data = helpers.load_yaml(graph_file_path)
    if not graph_data:
        raise Exception("Graph '%s' is empty." % graph_file_path)

    # Extract filename without extension from absolute path
    graph_name = os.path.splitext(os.path.split(graph_file_path)[-1])[0]

    # Upload graph to Nailgun
    client = graph.GraphClient()
    client.upload(graph_data, "clusters", env_id, graph_name)
    LOG.info("Graph '%s' uploaded for environment '%s'."
             % (graph_name, env_id))


def graphs_upload_for_cmd(cmd_name, orig_id=None, seed_id=None):
    """Upload graphs to Nailgun for specific command.

    Read and upload graphs for original and seed environemtns
    from "orig" and "seed" subfolders respectevly. Upload only
    graphs that contain command name in filename.
    """

    graph_path = os.path.join(magic_consts.DEPLOYMENT_DIR,
                              'puppet/octane_tasks/graphs')

    # Upload command graphs to original environment
    if orig_id:
        graph_path_orig = os.path.join(graph_path, 'orig')
        for filename in os.listdir(graph_path_orig):
            if not filename.endswith(".yaml"):
                continue
            if cmd_name in filename:
                graph_upload_to_env(os.path.join(graph_path_orig, filename),
                                    orig_id)

    # Upload command graphs to seed environment
    if seed_id:
        graph_path_seed = os.path.join(graph_path, 'seed')
        for filename in os.listdir(graph_path_seed):
            if not filename.endswith(".yaml"):
                continue
            if cmd_name in filename:
                graph_upload_to_env(os.path.join(graph_path_seed, filename),
                                    seed_id)


def graph_execute_and_wait(graph_type, env_id, timeout=3600):
    """Execute graph with fuelclient and wait until finished."""
    client = graph.GraphClient()
    graph_task = client.execute(env_id, None, graph_type=graph_type)

    started_at = time.time()
    check_freq = 30
    while True:
        status = graph_task.status

        # Return True if ready
        if status == 'ready':
            LOG.info("Graph '%s' for environment '%s' finished successfully."
                     % (graph_type, env_id))
            return True

        # Raise exception if error
        if status == 'error':
            raise Exception("Task '%s' with graph '%s' for environment '%s'"
                            " finished with error."
                            % (graph_task.id, graph_type, env_id))

        # Raise exception if timeout
        if time.time() - started_at >= timeout:
            raise Exception("Timeout waiting task '%s' execution"
                            " for graph '%s'." % (graph_task.id, graph_type))

        LOG.info("Graph '%s' for environment %s has status '%s'"
                 % (graph_type, env_id, status))

        time.sleep(check_freq)


def graph_list(env_id):
    """Return list with graph names(types)."""
    client = graph.GraphClient()
    # TODO: Take into account not only cluster graphs
    return [g['relations'][0]['type'] for g in client.list(env_id)]
