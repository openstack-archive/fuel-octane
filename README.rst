===============================
octane
===============================

Octane - upgrade your Fuel.

Tool set to backup, restore and upgrade Fuel installer and OpenStack
environments that it manages. This version of the toolset supports
upgrade from version 7.0 to version 8.0.

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/octane
* Source: http://git.openstack.org/cgit/stackforge/octane
* Bugs: http://bugs.launchpad.net/octane

Features
--------

* Backup the Fuel Master node configuraiton, OpenStack release bundles,
  metadata of environments and target nodes

* Restore metadata of the Fuel Master node, environments and target nodes
  from previous backup

* Upgrade OpenStack environment after upgrade of the Fuel Master node
  that manages it


Installation
------------

Fuel Octane is installed on the Fuel Master node. Version of ``fuel-octane``
package must match the version of Fuel.

To download the latest version of ``fuel-octane`` package on the Fuel Master
node, use the following command:

::

    yum instal fuel-octane

Usage
-----

.. note::

    Make sure that you install a latest Maintenance Update onto Fuel 7.0
    before making backup of configuration information.

Backup Fuel configuration
=========================

Use this command to backup configuration of the Fuel Master node, environments
and target nodes:

::

    octane fuel-backup --to=/path/to/backup.file.tar.gz

Backup Fuel repos and images
============================

Use this command to backup packages and images for all supported OpenStack
release bundles from the Fuel Master node:

::

    octane fuel-repo-backup --full --to=/path/to/repo-backup.file.tar.gz

Restore Fuel configuration
==========================

Use this command to restore configuration of the Fuel Master node, environments
and target nodes:

::

    octane fuel-restore --from=/path/to/backup.file.tar.gz --admin-password=<passwod>

Replace ``<password>`` with appropriate password for user ``admin`` in your
installation of Fuel.

Restore Fuel repos and images
=============================

Use this command to restore package repositories and images for OpenStack
release bundbles from backup file:

::

    octane fuel-repo-restore --from=/path/to/repo-backup.file.tar.gz

Upgrade Fuel Master node
========================

Upgrade of Fuel Master node requires making both backups of configuration
and repos and images from older Fuel, as described above. Copy those files
to a secure location. After you create two backup files, install a new
(8.0) version of Fuel on the same physical node or on a new one.

.. note::

    Please, note that you must specify the same IP address for the new
    installation of the Fuel Master node as for the old one. Otherwise,
    target nodes won't be able to communicate with the new Fuel Master
    node.

.. note::
    Make sure that you installed the latest available Maintenance Update
    onto the fresh installation of Fuel 8.0 before restoring configuration
    data on it.

Copy backup files to a new node from the secure location. Use ``octane`` to
restore Fuel configuration and packages from backup files. Database schema
will be upgraded according to migration scripts. See detailed commands above.

The Fuel Master node of new version must now have all configuration data from
an old version of the Fuel Master node.

Upgrade OpenStack cluster
=========================

Install 9.0 Seed environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pick environment of version 7.0 that you want to upgrade. Run the following
command and remember an ID of the environment you picked:

::

    export SEED_ID=<ID>

Run command to create Upgrade Seed environment:

::

    octane upgrade-env $SEED_ID

Remember ID of environment that will be shown:

::

    export ORIG_ID=<ID>

Upgrade controller #1
^^^^^^^^^^^^^^^^^^^^^

Pick controller with minimal ID:

::

    export $NODE_ID=<ID>

Run the following command to upgrade it:

::

    octane upgrade-node --isolated $SEED_ID $NODE_ID


Upgrade DB
^^^^^^^^^^

Run the following command to upgrade state database of OpenStack environment
to be upgraded:

::

    octane upgrade-db $ORID_ID $SEED_ID

Upgrade Ceph (OPTIONAL)
^^^^^^^^^^^^^^^^^^^^^^^

Run the command to upgrade Ceph cluster:

::

    octane upgrade-ceph $ORIG_ID $SEED_ID

Upgrade Ceph OSDs (OPTIONAL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use this step only when upgrade from version 7.0 or less, and only if you plan
to use live migration for minimal downtime.

The command below updates version of Ceph packages running on Ceph OSD nodes.

::

    octane upgrade-osd [-h] --admin-password <PASSWORD> $ORIG_ID

Cutover to the updated control plane
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following command redirects all nodes in OpenStack cluster to talk to
the new OpenStack Controller with upgraded version:

::

    octane upgrade-control $ORIG_ID $SEED_ID

Upgrade controller #2 and #3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run the following command to upgrade remaining controllers to version 8.0:

::

    octane upgrade-node $SEED_ID $NODE_ID_2 $NODE_ID_3

Upgrade computes
^^^^^^^^^^^^^^^^

Pick a compute node(s) to upgrade and remember their IDs.

::

    export NODE_ID_1=<ID1>
    ...

Run the command to upgrade the compute node(s) without evacuating virtual
machines:

::

    octane upgrade-node --no-live-migration $SEED_ID $NODE_ID_1 ...


Run the command to upgrade the compute node(s) with evacuating virtual
machines to other compute nodes in the environment via live migration:

::

    octane upgrade-node $SEED_ID $NODE_ID_1 ...

Clean up the environment
^^^^^^^^^^^^^^^^^^^^^^^^

Run the command to remove temporary configurations, including parameter
``upgrade_levels`` set in Nova configuration files at Controller and
Compute nodes:

::

    octane cleanup $SEED_ID
