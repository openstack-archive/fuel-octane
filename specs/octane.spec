%define name fuel-octane
%{!?version: %define version 1}
%{!?release: %define release 1}

Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Summary: MOS upgrade tool
URL:     https://github.com/Mirantis/octane
License: Apache
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot
Prefix: /opt
BuildRequires: git
BuildRequires: python-setuptools
BuildRequires: python-pbr
BuildArch: noarch

Requires:    git
Requires:    python
Requires:    python-setuptools
Requires:    python-paramiko
Requires:    python-stevedore
Requires:    python-fuelclient
Requires:    python-cliff

%description
Project is aimed to validate if more or less simple upgrade of MOS 5.1+

%prep
%setup -cq -n %{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version} && OSLO_PACKAGE_VERSION=%{version} python setup.py egg_info && cp octane.egg-info/PKG-INFO . && python setup.py build

%install
cd %{_builddir}/%{name}-%{version} && python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=%{_builddir}/%{name}-%{version}/INSTALLED_FILES && cp -vr octane/patches ${RPM_BUILD_ROOT} && echo /octane/patches/ >> %{_builddir}/%{name}-%{version}/INSTALLED_FILES


%files -f %{_builddir}/%{name}-%{version}/INSTALLED_FILES
%defattr(-,root,root)


%clean
rm -rf $RPM_BUILD_ROOT
