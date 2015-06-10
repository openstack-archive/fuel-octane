import copy

from nailgun.api.v1.handlers import base
from nailgun import consts
from nailgun.db import db
from nailgun import objects
from nailgun import utils

from octane import validators


class ClusterCloneHandler(base.BaseHandler):
    single = objects.Cluster
    validator = validators.ClusterCloneValidator

    @base.content
    def POST(self, cluster_id):
        """Create a clone of the cluster.
        """
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
        clone.attributes.generated = utils.dict_merge(
            clone.attributes.generated,
            cluster.attributes.generated)
        clone.attributes.editable = self.merge_attributes(
            cluster.attributes.editable,
            clone.attributes.editable)
        db().flush()
        return self.single.to_json(clone)

    @staticmethod
    def merge_attributes(a, b):
        """Merge values of editable attributes.

        :param a: a dict of editable attributes
        :param b: a dict of editable attributes
        """
        attrs = copy.deepcopy(b)
        for section, pairs in attrs.iteritems():
            if section not in a:
                continue
            a_values = a[section]
            for key, values in pairs.iteritems():
                if key != "metadata" and key in a_values:
                    values["value"] = a_values[key]["value"]
        return attrs
