PKGNAME := spin
SPECFILE := $(PKGNAME).spec
VERSION := $(shell awk '/Version:/ { print $$2 }' $(SPECFILE))
RELEASE := $(shell awk '/Release:/ { print $$2 }' $(SPECFILE) | sed -e 's|%{?dist}||g')

ENTERPRISE_PKGNAME := spin-enterprise
ENTERPRISE_SPECFILE := $(ENTERPRISE_PKGNAME).spec
ENTERPRISE_VERSION := $(shell awk '/Version:/ { print $$2 }' $(ENTERPRISE_SPECFILE))
ENTERPRISE_RELEASE := $(shell awk '/Release:/ { print $$2 }' $(ENTERPRISE_SPECFILE) | sed -e 's|%{?dist}||g')

SUBDIRS = bin docsrc etc share spin

BUILDARGS =

.PHONY: all clean install install-enterprise tag tag-enterprise changelog archive archive-enterprise srpm srpm-enterprise bumpver bumpver-enterprise

all:
	for dir in $(SUBDIRS); do make -C $$dir; done

clean:
	rm -f *.tar.gz
	for dir in $(SUBDIRS); do make -C $$dir clean; done

install:
	@if [ "$(DESTDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A destdir is required"; \
		exit 1; \
	fi
	@if [ "$(PYTHONLIBDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A pythonlibdir is required."; \
		exit 1; \
	fi
	mkdir -p $(PYTHONLIBDIR)
	mkdir -p $(DESTDIR)
	for dir in $(SUBDIRS); do make -C $$dir PYTHONLIBDIR=`cd $(PYTHONLIBDIR); pwd` DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

install-enterprise:
	@if [ "$(DESTDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A destdir is required"; \
		exit 1; \
	fi
	@if [ "$(PYTHONLIBDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A pythonlibdir is required."; \
		exit 1; \
	fi
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)
	cp -var spin $(DESTDIR)/$(PYTHONLIBDIR)
	./pycompile spin/modules/core/rpmbuild/logos-rpm/*.py
	./pycompile spin/modules/core/rpmbuild/logos-rpm/config/*.py

tag:
	@if [ "$(USERNAME)" != "" ]; then \
		hg tag --user "$(USERNAME)" -m "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE); \
	else \
		hg tag "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE); \
	fi
	@echo "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)"

tag-enterprise:
	@if [ "$(USERNAME)" != "" ]; then \
		hg tag --user "$(USERNAME)" -m "Tagged as $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION)-$(ENTERPRISE_RELEASE)" $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION)-$(ENTERPRISE_RELEASE); \
	else \
		hg tag "Tagged as $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION)-$(ENTERPRISE_RELEASE)" $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION)-$(ENTERPRISE_RELEASE); \
	fi
	@echo "Tagged as $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION)-$(ENTERPRISE_RELEASE)"

changelog:
	@hg log --style changelog > ChangeLog

archive:
	@hg archive --exclude spin-enterprise.spec \
                    --exclude 'spin/modules/core/rpmbuild/logos-rpm' \
		    -t tgz --prefix=$(PKGNAME)-$(VERSION) $(PKGNAME)-$(VERSION).tar.gz

archive-enterprise:
	@hg archive --include 'spin/modules/core/rpmbuild/logos-rpm' \
	            --include COPYING \
                    --include AUTHORS \
                    --include spin-enterprise.spec \
                    --include Makefile \
	            --include pycompile \
                    -t tgz --prefix=$(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION) $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION).tar.gz

srpm: archive
	@rpmbuild $(BUILDARGS) -ts $(PKGNAME)-$(VERSION).tar.gz  || exit 1
	@rm -f $(PKGNAME)-$(VERSION).tar.gz

srpm-enterprise: archive-enterprise
	@rpmbuild $(BUILDARGS) -ts $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION).tar.gz  || exit 1
	@rm -f $(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION).tar.gz

bumpver:
	@NEWSUBVER=$$((`echo $(VERSION) | cut -d . -f 3` + 1)) ; \
	NEWVERSION=`echo $(VERSION).$$NEWSUBVER |cut -d . -f 1-2,4` ; \
	changelog="`hg log --exclude spin/modules/core/rpmbuild/logos-rpm --exclude spin-enterprise.spec -r tip:$(PKGNAME)-$(VERSION)-$(RELEASE) --template "- {desc|strip|firstline} ({author})\n" 2> /dev/null || echo "- Initial Build"`"; \
	rpmlog="`echo "$$changelog" | sed -e 's/@.*>)/)/' -e 's/(.*</(/'`"; \
	DATELINE="* `date "+%a %b %d %Y"` `hg showconfig ui.username` - $$NEWVERSION-$(RELEASE)" ; \
	cl=`grep -n %changelog $(SPECFILE) | cut -d : -f 1` ; \
	tail --lines=+$$(($$cl + 1)) $(SPECFILE) > speclog ; \
	(head -n $$cl $(SPECFILE) ; echo "$$DATELINE" ; echo "$$rpmlog"; echo ""; cat speclog) > $(SPECFILE).new ; \
	mv $(SPECFILE).new $(SPECFILE); rm -f speclog; \
	sed -i "s/Version: $(VERSION)/Version: $$NEWVERSION/" $(SPECFILE)
	make changelog

bumpver-enterprise:
	@NEWSUBVER=$$((`echo $(ENTERPRISE_VERSION) | cut -d . -f 3` + 1)) ; \
	NEWENTERPRISE_VERSION=`echo $(ENTERPRISE_VERSION).$$NEWSUBVER |cut -d . -f 1-2,4` ; \
	changelog="`hg log --include spin/modules/core/rpmbuild/logos-rpm --include spin-enterprise-spec -r tip:$(ENTERPRISE_PKGNAME)-$(ENTERPRISE_VERSION)-$(ENTERPRISE_RELEASE) --template "- {desc|strip|firstline} ({author})\n" 2> /dev/null || echo "- Initial Build"`"; \
	rpmlog="`echo "$$changelog" | sed -e 's/@.*>)/)/' -e 's/(.*</(/'`"; \
	DATELINE="* `date "+%a %b %d %Y"` `hg showconfig ui.username` - $$NEWENTERPRISE_VERSION-$(ENTERPRISE_RELEASE)" ; \
	cl=`grep -n %changelog $(ENTERPRISE_SPECFILE) | cut -d : -f 1` ; \
	tail --lines=+$$(($$cl + 1)) $(ENTERPRISE_SPECFILE) > speclog ; \
	(head -n $$cl $(ENTERPRISE_SPECFILE) ; echo "$$DATELINE" ; echo "$$rpmlog"; echo ""; cat speclog) > $(ENTERPRISE_SPECFILE).new ; \
	mv $(ENTERPRISE_SPECFILE).new $(ENTERPRISE_SPECFILE); rm -f speclog; \
	sed -i "s/Version: $(ENTERPRISE_VERSION)/Version: $$NEWENTERPRISE_VERSION/" $(ENTERPRISE_SPECFILE); \

