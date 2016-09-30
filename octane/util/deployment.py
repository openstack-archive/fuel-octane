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


def get_cluster_graph_names(env_id):
    """Return a list with graph names(types)."""

    client = graph.GraphClient()
    # TODO: Take into account not only cluster graphs
    return [g['relations'][0]['type'] for g in client.list(env_id)]


def upload_graphs(orig_id, seed_id):
    """Upload upgrade graphs to Nailgun.

    Read and upload graphs for original and seed environemtns
    from "orig" and "seed" subfolders respectevly.
    """

    # Upload command graphs to original environment
    upload_graph(orig_id, "orig")

    # Upload command graphs to seed environment
    upload_graph(seed_id, "seed")


def upload_graph(env_id, subdirectory):
    graph_path = os.path.join(magic_consts.DEPLOYMENT_GRAPH_DIR, subdirectory)
    upload_graphs_to_env(graph_path, env_id)


def upload_graphs_to_env(directory, env_id):
    """Upload all YAML-files as graphs to an environment."""

    for filename in os.listdir(directory):
        if not filename.endswith(".yaml"):
            continue
        upload_graph_file_to_env(os.path.join(directory, filename), env_id)


def upload_graph_file_to_env(graph_file_path, env_id):
    """Upload a graph file to Nailgun for an environment."""

    # Try to load graph data
    graph_data = helpers.load_yaml(graph_file_path)
    if not graph_data:
        raise Exception("Graph '{0}' is empty.".format(graph_file_path))
    graph_name = os.path.splitext(os.path.basename(graph_file_path))[0]

    # Upload graph to Nailgun
    client = graph.GraphClient()
    client.upload(graph_data, "clusters", env_id, graph_name)
    LOG.info("Graph '%s' was uploaded for the environment '%s'.",
             graph_name, env_id)


def execute_graph_and_wait(graph_name, env_id, nodes=None,
                           attempts=120, attempt_delay=30):
    """Execute graph with fuelclient and wait until finished."""

    client = graph.GraphClient()
    graph_task = client.execute(env_id, graph_types=[graph_name], nodes=nodes)
    for i in xrange(attempts):
        status = graph_task.status
        if status == 'ready':
            LOG.info("Graph %s for environment %s finished successfully.",
                     graph_name, env_id)
            return
        elif status == 'error':
            raise Exception(
                "Task {0} with graph {1} for environment {2} finished with "
                "error.".format(graph_task.id, graph_name, env_id))
        LOG.info("Attempt %s: graph '%s' for environment %s has status %s",
                 i, graph_name, env_id, status)
        time.sleep(attempt_delay)
    raise Exception("Timeout waiting of {0} seconds for the task {1} "
                    "execution of the graph {2}."
                    .format(attempts * attempt_delay, graph_task.id,
                            graph_name))
