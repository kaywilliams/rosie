%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           spin-enterprise
Version:        0.9.1
Release:        1%{?dist}
Summary:        Provides additional Spin features

Group:          Applications/System
License:        GPLv2+
URL:            http://www.renditionsoftware.com/spin
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:      noarch

BuildRequires:  python

Requires:       rhn-client-tools
Requires:       spin
Requires:       spin-logos

%description
The Spin Enterprise package provides additional features for the Spin
appliance development tool. It allows automatic generation of a logos
RPM containing appliance-specific branding which is visible during
installation, system boot, user login and from the GNOME and KDE
desktops. It also allows connecting directly to Red Hat Network as an
input source for appliance packages.

%prep
%setup -q

%build

%install
%{__rm} -rf %{buildroot}
%{__make} --makefile Makefile.enterprise install DESTDIR=%{buildroot} PYTHONLIBDIR=%{python_sitelib}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/spin/modules/core/rpmbuild/logos-rpm*
%doc COPYING
%doc AUTHORS

%changelog
* Thu Oct 16 2008 Uday Prakash <uprakash@renditionsoftware.com> - 0.9.1-1
- Initial Build

