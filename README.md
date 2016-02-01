# Octane upgrade workflow

## Prerequisites

In this manual we assume that user manages their environment with Fuel 5.1.1 and
has successfully upgraded it to Fuel 7.0 with the standard procedure.

Environments with the following configuration can be upgraded with Octane:

- Ubuntu operating system
- HA Multinode deployment mode
- KVM Compute
- Neutron with VLAN segmentation
- Ceph backend for Cinder AND Glance (Optional)
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
[root@fuel bin]# yum install -y git python-pip python-paramiko
[root@fuel bin]# ./octane prepare
```

## Install 7.0 Seed environment

First, pick the environment of version 5.1.1 you want to upgrade. Log in to Fuel
Master node and run:

```
[root@fuel bin]# fuel env
````

Find the environment you selected for upgrade and remember its ID. We will refer
to it as `ORIG_ID` below.

Use Octane script to create Upgrade Seed environment.

```
[root@fuel bin]# octane upgrade-env <ORIG_ID>
```

Remember the ID of resulting environment for later use, or store it to variable.
We will refer to it as <SEED_ID> later on.

### Upgrade controller #1

Choose added controller nodes from the list of unallocated nodes:

TESTESTEST
```
[root@fuel bin]# fuel node | grep discover
```

Remember the IDs of the nodes and run the following command replacing <NODE_ID>
with that number:

```
[root@fuel bin]# octane -v --debug install-node --isolated <ORIG_ID> <SEED_ID> \
     <NODE_ID> [<NODE_ID>, ...]
```

This command will install controller(s)with version 7.0 in Upgrade Seed
environment.

### Upgrade State DB

State Database contains all metadata and status data of virtual resources in
your cloud environment. Octane transfers that data to 7.0 environment as a part
of upgrade of CIC using the following command:

```
[root@fuel bin]# octane upgrade-db <ORIG_ID> <SEED_ID>
```

Before it starts data transfer, Octane stops all services on 7.0 CICs, and
disables APIs on 5.1.1 CICs, putting the environment into **Maintenance mode**.

### Upgrade Ceph cluster (OPTIONAL)

Configuration of original Ceph cluster must be replicated to the 7.0
environment. Use the following command to update configuration and restart
Ceph monitor at 7.0 controller:

```
[root@fuel bin]# octane upgrade-ceph <ORIG_ID> <SEED_ID>
```

Verify the successful update using the following command:

```
[root@fuel bin]# ssh root@node-<NODE_ID> "ceph health"
```

## Replace CICs 5.1.1 with 7.0

Now start all services on 7.0 CICs with upgraded data and redirect Compute
nodes from 5.1.1 CICs to 7.0 CICs.

Following Octane script will start all services on 7.0 CICs, then disconnect 5.1
CICs from Management and Public networks, while keeping connection between CICs
themselves, and connect 7.0 CICs to those networks:

```
[root@fuel bin]# octane upgrade-control ORIG_ID SEED_ID
```

### Upgrade compute nodes

Select a node to upgrade from the list of nodes in 5.1.1 environment:

```
[root@fuel bin]# fuel node --env <ORIG_ID>
```

Run Octane script with 'upgrade-node' command to reassign node to 7.0
environment and upgrade it. You need to specify ID of the node as a second
argument.

```
[root@fuel bin]# octane upgrade-node <SEED_ID> <NODE_ID> [<NODE_ID> ...]
```

Repeat this process until all nodes are reassigned from 5.1.1 to 7.0 environment.

## Finish upgrade

### Clean up the Fuel Master node

Run 'cleanup-fuel' command to revert all changes made to components of the Fuel
installer and uninstall temporary packages.

```
[root@fuel bin]# ./octane cleanup-fuel
```
