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

## Install Octane

Unpack Octane tarball to /root/ directory. Change to bin/ directory of Octane.

```
[root@fuel ~]# cd /root/octane/octane/bin
```

Run Octane script to install necessary packages on Fuel master and patch
manifests and source code of components.

```
[root@fuel bin]# ./octane prepare-fuel
```

## Install 6.0 Seed environment

### Clone settings

First, pick the environment of version 5.1 you want to upgrade. Log in to Fuel
Master node and run:

```
[root@fuel bin]# fuel env
````

Find the environment you selected for upgrade and remember its ID. We will refer
to it as `ORIG_ID` below.

Now run Octane script to clone settings of your environment:

```
[root@fuel bin]# ./octane clone ORIG_ID
```

Remember ID of your Seed environment. We will refer to it as `SEED_ID`.

### Add nodes

Make sure that you have 3 nodes you want to serve as CICs in 6.0 environment
added to Fuel in 'discover' status.

```
[root@fuel bin]# fuel node | grep discover
```

### Provision nodes

Use Octane script to add all nodes in 'discover' status to Seed environment and
initiate provisioning of operating system to these nodes:

```
[root@fuel bin]# ./octane provision ORIG_ID SEED_ID
```

Wait for nodes to come to 'provisioned' state.

### Configure isolation

Use Octane script to configure network isolation of Seed environment and start
deployment of OpenStack services:

```
[root@fuel bin]# ./octane prepare ORIG_ID SEED_ID
[root@fuel bin]# ./octane deploy SEED_ID
```

Wait for all controller node in Seed environment to become 'ready':

```
[root@fuel bin]# fuel node --env SEED_ID | grep ready
```

There should be 3 nodes in output.

## Upgrade CICs to 6.0

This stage upgrades 5.1 controllers to version 6.0 by replacing them
with CICs of Seed environment.

### Upgrade State Database

State Database contains all metadata and status data of virtual resources in
your cloud environment. Octane transfers that data to 6.0 environment as a part
of upgrade of CIC.

Before it starts data transfer, Octane stops all services on 6.0 CICs, and
disables APIs on 5.1 CICs, putting the environment into **Maintenance mode**.

Run Octane script to upgrade databases:

```
[root@fuel bin]# ./octane upgrade-db ORIG_ID SEED_ID
```

### Update 6.0 Ceph cluster configuration

Use Octane script to configure Ceph Monitors to work with original Ceph cluster:

```
[root@fuel bin]# ./octane upgrade-ceph ORIG_ID SEED_ID
```

Once it updated Ceph configuration, the script restarts Ceph Monitors on all 6.0
CICs.

### Replace CICs 5.1 with 6.0

Now start all services on 6.0 CICs with upgraded data and redirect Compute
nodes from 5.1 CICs to 6.0 CICs.

Following Octane script will start all services on 6.0 CICs, then disconnect 5.1
CICs from Management and Public networks, while keeping connection between CICs
themselves, and connect 6.0 CICs to those networks:

```
[root@fuel bin]# ./octane upgrade-cics ORIG_ID SEED_ID
```

### Upgrade `nova-compute` to 6.0

Run following script to upgrade `nova-compute` and dependency packages on all
hypervisor hosts to version 6.0 without upgrading data plane (i.e. hypervisor,
operating system and kernel). This script installs 6.0 source for APT package
manager, updates versions of `nova-compute` package and its dependencies
(including Neutron agent), updates configuration file for Neutron agent to work
with new version of packages and restarts updated services.

Note that this script will affect all compute nodes in the environment.

```
[root@fuel bin]# ./octane upgrade-nova-compute ORIG_ID
```

## Upgrade nodes

### Pick node for upgrade

Select a node to upgrade from the list of nodes in 5.1 environment:

```
[root@fuel bin]# fuel node --env ORIG_ID
```

Run Octane script with 'upgrade-node' command to reassign node to 6.0
environment and upgrade it. You need to specify ID of the node as a second
argument.

```
[root@fuel bin]# ./octane upgrade-node SEED_ID NODE_ID
```

Repeat this process until all nodes are reassigned from 5.1 to 6.0 environment.

## Finish upgrade

### Cleanup 6.0 environment

Run Octane script with 'cleanup' command to delete pending services data from
state database.

```
[root@fuel bin]# ./octane cleanup SEED_ID
```
