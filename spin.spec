%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:    spin
Version: 1.0
Release: 1
Summary: The Spin Package builds customized distributions

License:   GPLv2+
Group:     Applications/System
URL:       http://www.renditionsoftware.com/products/spin
Source0:   %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch

##BuildRequires:

##Requires:

##Provides:

##Conflicts:

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
%{python_sitelib}/spin
%{_datadir}/spin
%{_bindir}/spin

%changelog
