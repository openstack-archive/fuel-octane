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

import argparse
import os

from octane.helpers import transformations


SKIP_TASKS = ["ceph_ready_check"]


def get_parser():
    parser = argparse.ArgumentParser(description="Remove patch ports from "
                                                 "deployment configuration "
                                                 "of environment")
    parser.add_argument("dirname",
                        help="Name of directory that contains deployment "
                             "configuration of environment.")
    subparsers = parser.add_subparsers()

    parser_a = subparsers.add_parser("skip_tasks",
                                     help="Remove patch ports.")
    parser_a.set_defaults(action=skip_tasks)
    return parser


def skip_tasks(tasks_config):

    def skip_task(tasks_config, task_id):
        for task in tasks_config:
            task_requires = task.get("requires", [])
            task_required = task.get("required_for", [])
            if task_id in task_requires:
                task["requires"].remove(task_id)
            if task_id in task_required:
                task["required_for"].remove(task_id)
            if task["id"] == task_id:
                tasks_config.remove(task)
        return tasks_config

    for task_id in SKIP_TASKS:
        tasks_config = skip_task(tasks_config, task_id)
    return tasks_config


def update_env_deployment_tasks(dirname, action, *args):
    filename = "deployment_tasks.yaml"
    tasks_file = os.path.join(dirname, filename)
    tasks_config = transformations.load_yaml_file(tasks_file)
    tasks_config = action(tasks_config)
    transformations.dump_yaml_file(tasks_config, tasks_file)


def main():
    args = get_parser().parse_args()

    update_env_deployment_tasks(args.dirname, args.action)


if __name__ == "__main__":
    main()
