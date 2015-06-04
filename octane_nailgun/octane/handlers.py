from nailgun.api.v1.handlers import base

from octane import manager


class ClusterCloneHandler(base.DeferredTaskHandler):
    log_message = u"Trying to start cloning environment '{env_id}'"
    log_error = u"Error during execution of cloning " \
                u"task on environment '{env_id}': {error}"
    task_manager = manager.ClusterCloneTaskManager
