import copy

from nailgun.api.v1.handlers import base
from nailgun import consts
from nailgun.db import db
from nailgun.logger import logger
from nailgun import objects
from nailgun.objects.serializers import network_configuration
from nailgun import utils

from octane import validators


class ClusterCloneHandler(base.BaseHandler):
    single = objects.Cluster
    validator = validators.ClusterCloneValidator
    network_serializers = {
        consts.CLUSTER_NET_PROVIDERS.neutron:
        network_configuration.NeutronNetworkConfigurationSerializer,
        consts.CLUSTER_NET_PROVIDERS.nova_network:
        network_configuration.NovaNetworkConfigurationSerializer,
    }

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
        data = self.checked_data()
        cluster = self.get_object_or_404(self.single, cluster_id)
        release = self.get_object_or_404(objects.Release, data["release_id"])
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
            "name": data["name"],
            "mode": cluster.mode,
            "status": consts.CLUSTER_STATUSES.new,
            "net_provider": cluster.net_provider,
            "grouping": consts.CLUSTER_GROUPING.roles,
            "release_id": release.id,
        }
        if cluster.net_provider == consts.CLUSTER_NET_PROVIDERS.neutron:
            data["net_segment_type"] = \
                cluster.network_config.segmentation_type
            data["net_l23_provider"] = cluster.network_config.net_l23_provider
        clone = self.single.create(data)
        clone.attributes.generated = utils.dict_merge(
            clone.attributes.generated,
            cluster.attributes.generated)
        clone.attributes.editable = self.merge_attributes(
            cluster.attributes.editable,
            clone.attributes.editable)
        nets_serializer = self.network_serializers[cluster.net_provider]
        nets = self.merge_nets(nets_serializer.serialize_for_cluster(cluster),
                               nets_serializer.serialize_for_cluster(clone))
        self.single.get_network_manager(instance=clone).update(clone, nets)
        db.commit()
        logger.debug("The cluster %s was created as a clone of the cluster %s",
                     clone.id, cluster.id)
        return self.single.to_json(clone)

    @staticmethod
    def merge_attributes(a, b):
        """Merge values of editable attributes.

        The values of the b attributes have precedence over the values
        of the a attributes.

        Added:
            common.
                puppet_debug = true
            additional_components.
                mongo = false
            external_dns.
                dns_list = "8.8.8.8"
            external_mongo.
                host_ip = ""
                mongo_db_name = "ceilometer"
                mongo_password = "ceilometer"
                mongo_replset = ""
                mongo_user = "ceilometer"
            external_ntp.
                ntp_list = "0.pool.ntp.org, 1.pool.ntp.org, 2.pool.ntp.org"
            murano_settings.
                murano_repo_url = "http://storage.apps.openstack.org/"
            provision.
                method = "image"
            storage.images_vcenter = false
            workloads_collector.
                password = "..."
                tenant = "services"
                user = "fuel_stats_user"
        Renamed:
            common.
                start_guests_on_host_boot ->
                resume_guests_state_on_host_boot
        Changed:
            repo_setup.repos (extended by additional items)
            common.libvirt_type = kvm | data (removed vcenter)
        Removed:
            common.
                compute_scheduler_driver
            nsx_plugin.
                connector_type
                l3_gw_service_uuid
                nsx_controllers
                nsx_password
                nsx_username
                packages_url
                transport_zone_uuid
            storage.volumes_vmdk = false
            vcenter.
                cluster
                host_ip
                use_vcenter
                vc_password
                vc_user
            zabbix.
                password
                username

        :param a: a dict with editable attributes
        :param b: a dict with editable attributes
        :returns: a dict with merged editable attributes
        """
        attrs = copy.deepcopy(b)
        for section, pairs in attrs.iteritems():
            if section == "repo_setup" or section not in a:
                continue
            a_values = a[section]
            for key, values in pairs.iteritems():
                if key != "metadata" and key in a_values:
                    values["value"] = a_values[key]["value"]
        return attrs

    @classmethod
    def merge_nets(cls, a, b):
        """Merge network settings.

        Some parameters are copied from a to b.

        :param a: a dict with network settings
        :param b: a dict with network settings
        :returns settings: a dict with merged network settings
        """
        settings = copy.deepcopy(b)
        source_networks = dict((n["name"], n) for n in a["networks"])
        for net in settings["networks"]:
            if net["name"] not in source_networks:
                continue
            source_net = source_networks[net["name"]]
            for key, value in net.iteritems():
                if (key not in ("cluster_id", "id", "meta", "group_id") and
                        key in source_net):
                    net[key] = source_net[key]
        settings_params = settings["networking_parameters"]
        source_params = a["networking_parameters"]
        for key, value in settings_params.iteritems():
            if key not in source_params:
                continue
            settings_params[key] = source_params[key]
        return settings
