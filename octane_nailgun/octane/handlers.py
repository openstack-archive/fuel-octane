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

        Creates a new cluster with specified name and release_id. The
        new cluster are created with parameters that are copied from the
        cluster with cluster_id. The values of the generated and
        editable attributes are just copied from one to the other.

        :param cluster_id: ID of the cluster to copy parameters from it
        :returns: JSON representation of the created cluster

        :http: * 200 (OK)
               * 404 (cluster or release did not found in db)
        """
        params = self.checked_data()
        cluster = self.get_object_or_404(self.single, cluster_id)
        release = self.get_object_or_404(objects.Release, params["release_id"])
        # TODO(ikharin): Here should be more elegant code that verifies
        #                release versions of the original cluster and
        #                the future cluster. The upgrade process itself
        #                is meaningful only to upgrade the cluster
        #                between the major releases.
        # TODO(ikharin): This method should properly handle the upgrade
        #                from one major release to another but now it's
        #                hardcoded to perform the upgrade from 5.1.1 to
        #                6.1 release.
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

        The values of the b attributes have precedence over the values
        of the a attributes.

        :param a: a dict of dicts with editable attributes
        :param b: a dict of dicts with editable attributes
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
