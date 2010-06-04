%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    solutionstudio
Version: 1.0 
Release: 1%{?dist}
Summary: Builds system solutions based on CentOS and Red Hat Enterprise Linux

License:   GPL
Group:     Applications/System
URL:       http://solutionstudio.org/solutionstudio
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
Requires: python-devel
Requires: python-lxml
Requires: python-setuptools
Requires: rhn-client-tools
Requires: rpm-build
Requires: yum

%description
SolutionStudio builds complete, self-contained system solutions 
based on CentOS and Red Hat Enterprise Linux. See 
http://solutionstudio.org for more information. 

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
%config(noreplace) %{_sysconfdir}/logrotate.d/solutionstudio
%{python_sitelib}/*
%{_bindir}/solutionstudio
%{_datadir}/solutionstudio
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%{_mandir}/man5/solutionstudio.conf.5.gz
%{_mandir}/man1/solutionstudio.1.gz

%changelog
* Thu Jun 03 2010 Kay Williams <kayw@solutionstudio.org> - 1.0-1

* Tue Jun 01 2010 Kay Williams <kayw@solutionstudio.org> - 0.9.1-1
- Initial Build
