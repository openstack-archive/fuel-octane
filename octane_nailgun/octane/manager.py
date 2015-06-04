from nailgun import consts
from nailgun.db import db
from nailgun.db.sqlalchemy import models
from nailgun.logger import logger
from nailgun.task import manager


class ClusterCloneTaskManager(manager.TaskManager):
    def execute(self):
        logger.debug(
            u"Trying to start cloning cluster '{0}'".format(
                self.cluster.name or self.cluster.id
            )
        )
        task = models.Task(name=consts.TASK_NAMES.deploy, cluster=self.cluster)
        db().add(task)
        db().commit()
        return task
