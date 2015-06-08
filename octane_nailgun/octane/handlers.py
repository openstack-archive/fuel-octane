from nailgun.api.v1.handlers import base
from nailgun import consts
from nailgun import objects

from octane import validators


class ClusterCloneHandler(base.BaseHandler):
    single = objects.Cluster
    validator = validators.ClusterCloneValidator

    @base.content
    def POST(self, cluster_id):
        params = self.checked_data()

        cluster = self.get_object_or_404(self.single, cluster_id)
        clone = self.single.create({
            "name": params["name"],
            "mode": consts.CLUSTER_MODES.ha_full,
            "status": consts.CLUSTER_STATUSES.new,
            "net_provider": consts.CLUSTER_NET_PROVIDERS.neutron,
            "grouping": consts.CLUSTER_GROUPING.roles,
            "release_id": params["release_id"],
        })
        return self.single.to_json(clone)
