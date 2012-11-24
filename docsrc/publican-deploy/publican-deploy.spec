%define brand deploy

Name:		publican-deploy
Summary:	Common documentation files for %{brand}
Version:	1.0
Release:	1%{?dist}
License:	GFDLv1.2
Group:		Applications/Text
Buildroot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Buildarch:	noarch
Source:		%{name}-%{version}.tgz
Requires:	publican >= 1.99
BuildRequires:	publican >= 1.99
URL:		http://www.deployproject.org

%description
This package provides common files and templates needed to build documentation
for %{brand} with publican.

%prep
%setup -q 

%build
publican build --formats=xml --langs=all --publish

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p -m755 $RPM_BUILD_ROOT%{_datadir}/publican/Common_Content
publican install_brand --path=$RPM_BUILD_ROOT%{_datadir}/publican/Common_Content

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README
%doc COPYING
%{_datadir}/publican/Common_Content/%{brand}

%changelog
* Sat Nov 24 2012  Kay Williams <kay@deployproject.org> 0.1
- Created Brand

