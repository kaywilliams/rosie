%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    systembuilder
Version: 1.8.0
Release: 1%{?dist}
Summary: Builds software appliances based on Red Hat, CentOS and Fedora Linux

License:   GPLv2+
Group:     Applications/System
URL:       http://www.renditionsoftware.com/systembuilder
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
Requires: netpbm-progs
Requires: python-devel
Requires: python-imaging
Requires: python-lxml
Requires: python-setuptools
Requires: rendition-common
Requires: rpm-build
Requires: syslinux
Requires: yum

%description
SystemBuilder is an administrator tool for automating system 
deployment and maintenance using compact, flexible, reliable
system distributions. See http://www.renditionsoftware.com for
more information. 

Note: Customers who create appliances based on RHEL will need to
separately purchase RHEL subscriptions for all installed systems.

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
%config(noreplace) %{_sysconfdir}/logrotate.d/systembuilder
%{python_sitelib}/*
%{_bindir}/systembuilder
%{_datadir}/systembuilder
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%doc docsrc/SDFR/SDFR.html
%doc docsrc/usermanual/UserManual.html
%doc docsrc/images*
%{_mandir}/man5/systembuilder.conf.5.gz
%{_mandir}/man1/systembuilder.1.gz

%changelog

* Thu Dec 10 2009 Kay Williams <kwilliams@renditionsoftware.com> - 0.8.1-1
- Initial Build
