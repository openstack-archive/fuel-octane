import copy

from nailgun.api.v1.handlers import base
from nailgun import consts
from nailgun.db import db
from nailgun.db.sqlalchemy import models
from nailgun.errors import errors
from nailgun.logger import logger
from nailgun import objects
from nailgun.objects.serializers import network_configuration
from nailgun import rpc
from nailgun.settings import settings
from nailgun.task import task as tasks
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
        orig_cluster = self.get_object_or_404(self.single, cluster_id)
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
            "mode": orig_cluster.mode,
            "status": consts.CLUSTER_STATUSES.new,
            "net_provider": orig_cluster.net_provider,
            "grouping": consts.CLUSTER_GROUPING.roles,
            "release_id": release.id,
        }
        if orig_cluster.net_provider == consts.CLUSTER_NET_PROVIDERS.neutron:
            data["net_segment_type"] = \
                orig_cluster.network_config.segmentation_type
            data["net_l23_provider"] = \
                orig_cluster.network_config.net_l23_provider
        new_cluster = self.single.create(data)
        new_cluster.attributes.generated = utils.dict_merge(
            new_cluster.attributes.generated,
            orig_cluster.attributes.generated)
        new_cluster.attributes.editable = self.merge_attributes(
            orig_cluster.attributes.editable,
            new_cluster.attributes.editable)
        nets_serializer = self.network_serializers[orig_cluster.net_provider]
        nets = self.merge_nets(
            nets_serializer.serialize_for_cluster(orig_cluster),
            nets_serializer.serialize_for_cluster(new_cluster))
        net_manager = self.single.get_network_manager(instance=new_cluster)
        net_manager.update(new_cluster, nets)
        self.copy_vips(orig_cluster, new_cluster)
        net_manager.assign_vips_for_net_groups(new_cluster)
        logger.debug("The cluster %s was created as a clone of the cluster %s",
                     new_cluster.id, orig_cluster.id)
        return self.single.to_json(new_cluster)

    @staticmethod
    def copy_vips(orig_cluster, new_cluster):
        orig_vips = {}
        for ng in orig_cluster.network_groups:
            vips = db.query(models.IPAddr).filter(
                models.IPAddr.network == ng.id,
                models.IPAddr.node.is_(None),
                models.IPAddr.vip_type.isnot(None),
            ).all()
            orig_vips[ng.name] = list(vips)

        new_vips = []
        for ng in new_cluster.network_groups:
            orig_ng_vips = orig_vips.get(ng.name)
            for vip in orig_ng_vips:
                ip_addr = models.IPAddr(
                    network=ng.id,
                    ip_addr=vip.ip_addr,
                    vip_type=vip.vip_type,
                )
                new_vips.append(ip_addr)
        db.add_all(new_vips)
        db.commit()

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
        :returns: a dict with merged network settings
        """
        new_settings = copy.deepcopy(b)
        source_networks = dict((n["name"], n) for n in a["networks"])
        for net in new_settings["networks"]:
            if net["name"] not in source_networks:
                continue
            source_net = source_networks[net["name"]]
            for key, value in net.iteritems():
                if (key not in ("cluster_id", "id", "meta", "group_id") and
                        key in source_net):
                    net[key] = source_net[key]
        networking_params = new_settings["networking_parameters"]
        source_params = a["networking_parameters"]
        for key, value in networking_params.iteritems():
            if key not in source_params:
                continue
            networking_params[key] = source_params[key]
        return new_settings


class UpgradeNodeAssignmentHandler(base.BaseHandler):
    validator = validators.UpgradeNodeAssignmentValidator

    @classmethod
    def get_netgroups_map(cls, orig_cluster, new_cluster):
        netgroups = dict((ng.name, ng.id)
                         for ng in orig_cluster.network_groups)
        mapping = dict((netgroups[ng.name], ng.id)
                       for ng in new_cluster.network_groups)
        orig_admin_ng = cls.get_admin_network_group(orig_cluster)
        admin_ng = cls.get_admin_network_group(new_cluster)
        mapping[orig_admin_ng.id] = admin_ng.id
        return mapping

    @staticmethod
    def get_admin_network_group(cluster):
        query = db().query(models.NetworkGroup).filter_by(
            name="fuelweb_admin",
        )
        default_group = objects.Cluster.get_default_group(cluster)
        admin_ng = query.filter_by(group_id=default_group.id).first()
        if admin_ng is None:
            admin_ng = query.filter_by(group_id=None).first()
            if admin_ng is None:
                raise errors.AdminNetworkNotFound()
        return admin_ng

    @base.content
    def POST(self, cluster_id):
        cluster = self.get_object_or_404(objects.Cluster, cluster_id)
        data = self.checked_data()
        node_id = data["node_id"]
        node = self.get_object_or_404(objects.Node, node_id)

        netgroups_mapping = self.get_netgroups_map(node.cluster, cluster)

        orig_roles = node.roles

        objects.Node.update_roles(node, [])  # flush
        objects.Node.update_pending_roles(node, [])  # flush

        node.replaced_deployment_info = []
        node.deployment_info = []
        node.kernel_params = None
        node.cluster_id = cluster.id
        node.group_id = None

        objects.Node.assign_group(node)  # flush
        objects.Node.update_pending_roles(node, orig_roles)  # flush

        for ip in node.ip_addrs:
            ip.network = netgroups_mapping[ip.network]

        nic_assignments = db.query(models.NetworkNICAssignment).\
            join(models.NodeNICInterface).\
            filter(models.NodeNICInterface.node_id == node.id).\
            all()
        for nic_assignment in nic_assignments:
            nic_assignment.network_id = \
                netgroups_mapping[nic_assignment.network_id]

        bond_assignments = db.query(models.NetworkBondAssignment).\
            join(models.NodeBondInterface).\
            filter(models.NodeBondInterface.node_id == node.id).\
            all()
        for bond_assignment in bond_assignments:
            bond_assignment.network_id = \
                netgroups_mapping[bond_assignment.network_id]

        objects.Node.add_pending_change(node,
                                        consts.CLUSTER_CHANGES.interfaces)

        node.pending_addition = True
        node.pending_deletion = False

        task = models.Task(name=consts.TASK_NAMES.node_deletion,
                           cluster=cluster)
        db.add(task)

        db.commit()

        self.delete_node_by_astute(task, node)

    @staticmethod
    def delete_node_by_astute(task, node):
        node_to_delete = tasks.DeletionTask.format_node_to_delete(node)
        msg_delete = tasks.make_astute_message(
            task,
            'remove_nodes',
            'remove_nodes_resp',
            {
                'nodes': [node_to_delete],
                'check_ceph': False,
                'engine': {
                    'url': settings.COBBLER_URL,
                    'username': settings.COBBLER_USER,
                    'password': settings.COBBLER_PASSWORD,
                    'master_ip': settings.MASTER_IP,
                }
            }
        )
        rpc.cast('naily', msg_delete)
