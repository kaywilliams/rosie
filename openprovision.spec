%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    openprovision
Version: 1.0.7
Release: 1%{?dist}
Summary: Platform for provisioning CentOS and Red Hat Enterprise Linux Systems

License:   GPL
Group:     Applications/System
URL:       http://www.openprovision.com/openprovision
Source0:   %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch

BuildRequires: docbook-style-xsl
BuildRequires: gzip
BuildRequires: libxml2
BuildRequires: libxslt
BuildRequires: python

Requires: createrepo
Requires: dosfstools
Requires: gnupg
Requires: mkisofs
Requires: pykickstart
Requires: python-devel
Requires: python-hashlib
Requires: python-lxml
Requires: python-setuptools
Requires: rhn-client-tools
Requires: rpm-build
Requires: syslinux
Requires: yum

%description
OpenProvision is a complete platform for IT professionals to automate build, 
test, deployment and maintenance of CentOS and Red Hat Enterprise Linux
systems for use in any physical, virtual or cloud environment. See 
http://www.openprovision.com for more information. 

%prep
%setup -q

%build
%{__make}

%install
%{__rm} -rf %{buildroot}
%{__make} install DESTDIR=%{buildroot} PYTHONLIBDIR=%{python_sitelib}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/logrotate.d/openprovision
%{python_sitelib}/*
%{_bindir}/openprovision
%{_datadir}/openprovision
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%{_mandir}/man5/openprovision.conf.5.gz
%{_mandir}/man1/openprovision.1.gz

%changelog
* Mon Jul 08 2011 Kay Williams <kwilliams@openprovision.com> - 0.9.1-1
- Initial Build
