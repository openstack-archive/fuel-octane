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
        release = self.get_object_or_404(objects.Release, params["release_id"])
        data = {
            "name": params["name"],
            "mode": cluster.mode,
            "status": consts.CLUSTER_STATUSES.new,
            "net_provider": cluster.net_provider,
            "grouping": consts.CLUSTER_GROUPING.roles,
            "release_id": release.id,
        }
        if cluster.net_provider == consts.CLUSTER_NET_PROVIDERS.neutron:
            data["net_segmentation_type"] = \
                cluster.network_config.segmentation_type
            data["net_l23_provider"] = cluster.network_config.net_l23_provider
        clone = self.single.create(data)
        return self.single.to_json(clone)
