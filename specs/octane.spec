%define name octane
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
BuildArch: noarch

Requires:    python
Requires:    patch
Requires:    pip
Requires:    tar
Requires:    pssh
Requires:    python-pbr
Requires:    python-setuoptools


%define _prefix /opt/

%description
Project is aimed to validate if more or less simple upgrade of MOS 5.1+

%prep
%setup 

%build

%install
install -d -m 755 $RPM_BUILD_ROOT/opt/%{name}
cp -rf * $RPM_BUILD_ROOT/opt/%{name} 

%clean
rm -rf $RPM_BUILD_ROOT
