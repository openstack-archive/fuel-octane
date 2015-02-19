# Octane upgrade workflow

## Prerequisites

In this manual we assume that user manages their environment with Fuel 5.1 and
has successfully upgraded it to Fuel 6.0 with the standard procedure.

Environments with the following configuration can be upgraded with Octane:

- Ubuntu operating system
- HA Multinode deployment mode
- KVM Compute
- Neutron with VLAN segmentation
- Ceph backend for Cinder AND Glance
- No additional services instlled (like Sahara, Murano, Ceilometer, etc)

## Clean up nodes for 6.0 Seed environment

This is an optional step. Select nodes in your environment and use live
migration to evacuate all virtual instances from the node. Delete the node from
environment. Repeat for at least 2 nodes (CIC and Compute/Ceph OSD in 6.0 Seed
environment). Wait for nodes to be discovered in Fuel as `unallocated'.

## Install 6.0 Seed environment

### Clone settings

First, pick the environment of version 5.1 you want to upgrade. Log in to Fuel
Master node and run:

```
fuel env
````

Find the environment you selected for upgrade and remember its ID. We will refer
to it as `ORIG_ID` below.

Now run Octane script to clone settings of your environment:

```
octane/bin/deploy-with-gre-isolation.sh clone ORIG_ID
```

Remember ID of your Seed environment. We will refer to it as `SEED_ID`.

### Add nodes

Add nodes from pool of unallocated node to the new environment via Fuel UI or
CLI. You need to add at least 1 CIC and at least 1 Ceph-OSD node. You may add
Compute node, but it is optional.

Configure disks and interfaces at nodes in Seed environment via Fuel UI.

### Provision nodes

Use Octane script to initiate provisioning of operating system to all nodes in
Seed environment:

```
octane/bin/deploy-with-gre-isolation.sh provision ORIG_ID SEED_ID
```

Wait for nodes to come to 'provisioned' state.

### Patch Fuel manifests

While Seed environment is being provisioned, patch Fuel manifests using
following Octane script:

```
octane/bin/patch-fuel-manifests.sh
```

### Configure isolation

Use Octane script to configure network isolation of Seed environment and start
deployment of OpenStack services:

```
octane/bin/deploy-with-gre-isolation.sh deploy ORIG_ID SEED_ID
```

Wait for Seed environment to come into 'operational' state:

```
fuel env --env SEED_ID
```

## Upgrade CICs to 6.0

This stage upgrades 5.1 controllers to version 6.0 by replacing them
with CICs of Seed environment.

### Shut off CIC services

Use Octane script to shut off OpenStack services on CICs in 5.1
environment:

```
octane/bin/manage_services.sh disable ORIG_ID
```

Shut off OpenStack services on 6.0 CIC:

```
octane/bin/manage_services.sh stop SEED_ID
```

Disable OpenStack API servers on 6.0 CICs:

```
octane/bin/manage_services.sh disable SEED_ID
```

### Configure 6.0 CIC

Modify configuration of 6.0 CIC to ensure compatibility with 5.1 Computes:

```
octane/bin/manage_services.sh config SEED_ID icehouse
```

### Upgrade State Database

State Database contains all metadata and status data of virtual resources in
your cloud environment. Octane transfers that data to 6.0 environment as a part
of upgrade of CIC.

Run Octane script to upgrade databases:

```
octane/bin/upgrade-db.sh ORIG_ID SEED_ID
```

### Remove 6.0 CICs isolation

At this point, we need to lift isolation from 6.0 CICs. Before that, bring down
VIPs of 6.0 environment to avoid IP address conflicts:

```
octane/bin/manage_services.sh stop_vips SEED_ID
```

### Update 6.0 Ceph cluster configuration

Use Octane script to configure Ceph Monitors to work with original Ceph cluster:

```
octane/bin/migrate-ceph-mon.sh ORIG_ID SEED_ID
```

### Start 6.0 CIC services

Once DB upgraded and Ceph MONs reconfigured, run Octane script to start services
on 6.0 CICs:

```
octane/bin/manage_services.sh start SEED_ID
```

### Replace CICs 5.1 with 6.0

### Move Neutron resources to 6.0 CICs

## Upgrade Compute to 6.0


