# Octane upgrade workflow

## Prerequisites

In this manual we assume that user manages their environment with Fuel 5.1 and
has successfully upgraded it to Fuel 6.1 with the standard procedure.

Environments with the following configuration can be upgraded with Octane:

- Ubuntu operating system
- HA Multinode deployment mode
- KVM Compute
- Neutron with VLAN segmentation
- Ceph backend for Cinder AND Glance
- No additional services installed (like Sahara, Murano, Ceilometer, etc)

## Install Octane

Create archive from this repository with `git archive` command and copy it to
your Fuel Master host.

Unpack Octane tarball to /root/ directory. Change to bin/ directory of Octane.

```
[root@fuel ~]# cd /root/octane/octane/bin
```

Run Octane script to install necessary packages on Fuel master and patch
manifests and source code of components.

```
[root@fuel bin]# ./octane prepare
```

## Install 6.1 Seed environment

First, pick the environment of version 5.1.1 you want to upgrade. Log in to Fuel
Master node and run:

```
[root@fuel bin]# fuel env
````

Find the environment you selected for upgrade and remember its ID. We will refer
to it as `ORIG_ID` below.

Use Octane script to create Upgrade Seed environment.

```
[root@fuel bin]# ./octane upgrade-env <ORIG_ID>
```

Remember the ID of resulting environment for later use, or store it to variable.
We will refer to it as <SEED_ID> later on.

### Upgrade controller #1

Choose a controller node from the list of nodes in 5.1.1 environment:

```
[root@fuel bin]# fuel node --env <ORIG_ID>
```

Remember the ID of the node and run the following command replacing <NODE_ID>
with that number:

```
[root@fuel bin]# ./octane upgrade-node <SEED_ID> <NODE_ID> isolated
```

This command will move the node to Seed environment and install it as a primary
controller with version 6.1.

### Upgrade State DB

State Database contains all metadata and status data of virtual resources in
your cloud environment. Octane transfers that data to 6.1 environment as a part
of upgrade of CIC using the following command:

```
[root@fuel bin]# ./octane upgrade-db <ORIG_ID> <SEED_ID>
```

Before it starts data transfer, Octane stops all services on 6.1 CICs, and
disables APIs on 5.1.1 CICs, putting the environment into **Maintenance mode**.

### Upgrade Ceph cluster

Configuration of original Ceph cluster must be replicated to the 6.1
environment. Use the following command to update configuration and restart
Ceph monitor at 6.1 controller:

```
[root@fuel bin]# ./octane upgrade-ceph <ORIG_ID> <SEED_ID>
```

Verify the successful update using the following command:

```
[root@fuel bin]# ssh root@node-<NODE_ID> "ceph health"
```

## Replace CICs 5.1.1 with 6.1

Now start all services on 6.1 CICs with upgraded data and redirect Compute
nodes from 5.1.1 CICs to 6.1 CICs.

Following Octane script will start all services on 6.1 CICs, then disconnect 5.1
CICs from Management and Public networks, while keeping connection between CICs
themselves, and connect 6.1 CICs to those networks:

```
[root@fuel bin]# ./octane upgrade-cics ORIG_ID SEED_ID
```

## Upgrade nodes

### Upgrade controllers

Now you have all your hypervisors working with single 6.1 controller from the
Seed environment. Upgrade your 5.1.1 controllers to get HA 6.1 OpenStack
cluster. Use the following command, replacing <NODE_ID> with ID of controller
you are going to upgrade this time:

```
[root@fuel bin]# ./octane upgrade-node <SEED_ID> <NODE_ID>

### Upgrade compute nodes

Select a node to upgrade from the list of nodes in 5.1.1 environment:

```
[root@fuel bin]# fuel node --env <ORIG_ID>
```

Run Octane script with 'upgrade-node' command to reassign node to 6.1
environment and upgrade it. You need to specify ID of the node as a second
argument.

```
[root@fuel bin]# ./octane upgrade-node <SEED_ID> <NODE_ID>
```

Repeat this process until all nodes are reassigned from 5.1.1 to 6.1 environment.

## Finish upgrade

### Cleanup 6.1 environment

Run Octane script with 'cleanup' command to delete pending services data from
state database.

```
[root@fuel bin]# ./octane cleanup <SEED_ID>
```
