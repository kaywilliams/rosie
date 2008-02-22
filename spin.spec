%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    spin
Version: 0.0
Release: 1
Summary: The Spin Package builds customized distributions

License:   GPLv2+
Group:     Applications/System
URL:       http://www.renditionsoftware.com/products/spin
Source0:   %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch

BuildRequires: python-devel
BuildRequires: python-docutils

Requires: ImageMagick
Requires: anaconda-runtime
Requires: createrepo
Requires: python-imaging
Requires: python-lxml
Requires: python-setuptools
Requires: rendition-common
Requires: syslinux
Requires: yum

%description
The spin package contains the necessary shared server applications to build
and run a Spin-managed distribution.

%prep
%setup -q

%build
%{__make} depend

%install
%{__rm} -rf %{buildroot}
%{__make} install DESTDIR=%{buildroot}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc COPYING
%doc ChangeLog
%doc AUTHORS
%doc INSTALL
%doc README
%doc NEWS
%doc share/doc/examples
%{python_sitelib}/spin
%{_datadir}/spin
%{_bindir}/spin
%{_mandir}/man5/spin.conf.5.gz
%{_mandir}/man5/distro.conf.5.gz

%changelog
