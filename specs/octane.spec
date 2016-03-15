%define name fuel-octane
%{!?version: %define version 9.0.0}
%{!?release: %define release 1}

Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Summary: Fuel/MOS upgrade tool
URL:     https://github.com/openstack/fuel-octane
License: Apache
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot
Prefix: %{_prefix}
BuildRequires: git
BuildRequires: python-setuptools
BuildRequires: python-pbr
BuildArch: noarch

Requires:    git
Requires:    patch
Requires:    python
Requires:    python-setuptools
Requires:    python-paramiko
Requires:    python-stevedore
Requires:    python-fuelclient
Requires:    python-cliff

%description
Project is aimed to provide tools to upgrade the Fuel Admin node and OpenStack
installations to version 9.0.

%prep
%setup -cq -n %{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version} && %{__python2} setup.py build

%install
install -d ${RPM_BUILD_ROOT}/usr/share/octane
cd %{_builddir}/%{name}-%{version} && %{__python2} setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT
cp -vr %{_builddir}/%{name}-%{version}/octane/patches ${RPM_BUILD_ROOT}/usr/share/octane/

%files
%defattr(-,root,root)
%{python2_sitelib}/*
%{_bindir}/octane
%{_datadir}/octane/*

%clean
rm -rf $RPM_BUILD_ROOT
