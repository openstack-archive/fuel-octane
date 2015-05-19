..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Upgrade An OpenStack Environment To A New Major Release
=======================================================

https://blueprints.launchpad.net/fuel/+spec/upgrade-major-openstack-environment

Supporting Mirantis OpenStack environment beyond single major release requires
that the deployment automation engine that manages the environment allows to
upgrade Mirantis OpenStack control plane and data plane software between major
releases.


Problem description
===================

Mirantis OpenStack follows closely the upstream OpenStack release cycle. New
features must be made available to users of Fuel with minimal impact on their
workloads, i.e. virtual machines, connected virtual resources and applications
that run on top of this infrastructure.

The upgrade of OpenStack environment should involves upgrade of the following
components:

* Deployment automation engine (Fuel installer) to support installation of
  software of the new release.

* OpenStack control plane services on Controller nodes, Compute nodes, including
  API servers and others.

* Upgrade platform control plane services on Controller nodes (e.g. Ceph MONs).

* Upgrade data plane software, including hypervisor, virtual switches, kernel
  etc.


Proposed change
===============

We propose to develop and implement a solution that allows to upgrade Mirantis
OpenStack environment from version 6.1 to version 7.0. This solution will rely
on certain functions of the Fuel installer, and will have external component
that orchestrates the upgrade process.

This proposal only covers external upgrade orchestration script. Implementation
of functions of Fuel installer used by this script are out of scope of this
proposal.

Upgrade strategy implemented in the proposed upgrade script involves
installation of new Controllers side by side with the ones being upgraded.
Resource nodes are redirected to the new Controllers and eventually upgraded
with minimal move of data. Under Resource nodes we understand nodes with Compute
and/or Storage roles. Resource nodes are upgraded 'in place', i.e. on the same
hardware, keeping user data intact on storage devices separated from Operating
System boot device on the node.

The reason to have external script that performs operations outlined above is
that it have to orchestrate at least 2 OpenStack environments: the original one
picked for upgrade and the new one, upgraded. Fuel currently can only handle a
single environment at a time. It doesn't have a component that can orchestrate
multiple environments.


Alternatives
------------

The side-by-side strategy of upgrade of a cloud has an alternative of fully
in-place solution. In that case, no data must be moved wahtsoever. All software
components are updated on the same set of hardware. Metadata is converted into
format of the new version. Data remains where it was.

This type of upgrade, in theory, must be more seamless then side-by-side
variant. However, in complex architectures like HA Mirantis OpenStack Reference
Architecture, multiple components that interact with each other make it
extremeliy difficult. Various race conditions in upgrade flow can cause severe
interruptions to the virtual infrastructure and workloads running on top of it.

The eventual goal of upgrade user story in Mirantis OpenStack is to make it
possible to upgrade OpenStack control plane and data plane in-place without
interruption of virtual resources and end user's workloads.


Data model impact
-----------------

Upgrade script itself does not require any changes in Fuel or OpenStack data
models. Accompanying proposals for new functions in Fuel that the upgrade script
uses, on the other hand, might have impact on data models. That impact is
described in the corresponding specifications.


REST API impact
---------------

Upgrade script doesn't have an impact on REST API. Supporting features proposed
to Fuel might have such an impact. This is described in corresponding
specifications in more details.


Upgrade impact
--------------

This change implements the upgrade process as an external script that
orchestrates 2 OpenStack environments: original and new version.

Proposed solution depends on the ability to upgrade the Fuel Master node.


Security impact
---------------

Upgrade is a high-risk procedure from security standpoint. It requires
administrative access to both environments involved in upgrade.

Notifications impact
--------------------

No impact.


Other end user impact
---------------------

End users of upgrade script are cloud operators wanting to upgrade their clouds.
This proposal introduces a new CLI tool for them that guides them through the
upgrade procedure.


Performance Impact
------------------

No impact.


Plugin impact
-------------

No impact.


Other deployer impact
---------------------

Proposed script can be packaged as a Python application and distributed with
Fuel as a part of Fuel repository, or separately via Python package management
system (``pip``)


Developer impact
----------------

No impact.


Infrastructure impact
---------------------

This change will require the whole Upgrade CI infrastructure to be built. This
script must be run against any changes that are being backported to 7.0 branch.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gelbuhos

Other contributors:


Work Items
----------



Dependencies
============

* Include specific references to specs and/or blueprints in fuel, or in other
  projects, that this one either depends on or is related to.

* If this requires functionality of another project that is not currently used
  by Fuel, document that fact.

* Does this feature require any new library dependencies or code otherwise not
  included in Fuel? Or does it depend on a specific version of library?


Testing
=======

Testing of the script itself will require lab with two versions Fuel Master node
to be set up:

* Fuel 5.1.1 must be installed and environment created by it
* The Fuel Master node must be upgraded to version 7.0 (potentially through
  version 6.x as an interim stage)
* Script shall be executed on the Fuel Master node.
* Environment of version 7.0 will be created with a set of Controller nodes.
* Compute/Storage nodes will be moved from original version 5.1.1 environment to
  the new 7.0 environment.
* Integration tests must validate that the resulting environment has all the
  capabilities and parameters of the original environment.
* Functional tests must validate impact on the cloud end user's workloads.


Documentation Impact
====================

Documentation for the upgrade script must be integrated into Operations Guide.
It must replace the description of the experimental manual upgrade procedure
from 5.1.1 to 6.0.

References
==========

