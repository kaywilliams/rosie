PKGNAME := spin
SPECFILE := $(PKGNAME).spec
VERSION := $(shell awk '/Version:/ { print $$2 }' $(SPECFILE))
RELEASE := $(shell awk '/Release:/ { print $$2 }' $(SPECFILE) | sed -e 's|%{?dist}||g')

EXTRAS_PKGNAME := spin-extras
EXTRAS_SPECFILE := $(EXTRAS_PKGNAME).spec
EXTRAS_VERSION := $(shell awk '/Version:/ { print $$2 }' $(EXTRAS_SPECFILE))
EXTRAS_RELEASE := $(shell awk '/Release:/ { print $$2 }' $(EXTRAS_SPECFILE) | sed -e 's|%{?dist}||g')

SUBDIRS = bin docsrc etc share spin

BUILDARGS =

.PHONY: all build installextras clean install tag changelog archive srpm bumpver

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

installextras:
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

changelog:
	@hg log --style changelog > ChangeLog

archive:
	@hg archive -t tgz --prefix=$(PKGNAME)-$(VERSION) $(PKGNAME)-$(VERSION).tar.gz

archiveextras:
	@hg archive --include 'spin/modules/core/rpmbuild/logos-rpm' \
	            --include COPYING \
                    --include AUTHORS \
                    --include spin-extras.spec \
                    --include Makefile \
	            --include pycompile \
                    -t tgz --prefix=$(EXTRAS_PKGNAME)-$(EXTRAS_VERSION) $(EXTRAS_PKGNAME)-$(EXTRAS_VERSION).tar.gz

srpm: archive
	@rpmbuild $(BUILDARGS) -ts $(PKGNAME)-$(VERSION).tar.gz  || exit 1
	@rm -f $(PKGNAME)-$(VERSION).tar.gz

srpmextras: archiveextras
	@rpmbuild $(BUILDARGS) -ts $(EXTRAS_PKGNAME)-$(EXTRAS_VERSION).tar.gz  || exit 1
	@rm -f $(EXTRAS_PKGNAME)-$(EXTRAS_VERSION).tar.gz

bumpver:
	@NEWSUBVER=$$((`echo $(VERSION) | cut -d . -f 3` + 1)) ; \
	NEWVERSION=`echo $(VERSION).$$NEWSUBVER |cut -d . -f 1-2,4` ; \
	changelog="`hg log -r tip:$(PKGNAME)-$(VERSION)-$(RELEASE) --template "- {desc|strip|firstline} ({author})\n" 2> /dev/null || echo "- Initial Build"`"; \
	rpmlog="`echo "$$changelog" | sed -e 's/@.*>)/)/' -e 's/(.*</(/'`"; \
	DATELINE="* `date "+%a %b %d %Y"` `hg showconfig ui.username` - $$NEWVERSION-$(RELEASE)" ; \
	cl=`grep -n %changelog $(SPECFILE) | cut -d : -f 1` ; \
	tail --lines=+$$(($$cl + 1)) $(SPECFILE) > speclog ; \
	(head -n $$cl $(SPECFILE) ; echo "$$DATELINE" ; echo "$$rpmlog"; echo ""; cat speclog) > $(SPECFILE).new ; \
	mv $(SPECFILE).new $(SPECFILE); rm -f speclog; \
	sed -i "s/Version: $(VERSION)/Version: $$NEWVERSION/" $(SPECFILE); \
	@make changelog

bumpverextras:
	@NEWSUBVER=$$((`echo $(EXTRAS_VERSION) | cut -d . -f 3` + 1)) ; \
	NEWEXTRAS_VERSION=`echo $(EXTRAS_VERSION).$$NEWSUBVER |cut -d . -f 1-2,4` ; \
	changelog="`hg log -r tip:$(EXTRAS_PKGNAME)-$(EXTRAS_VERSION)-$(EXTRAS_RELEASE) --template "- {desc|strip|firstline} ({author})\n" 2> /dev/null || echo "- Initial Build"`"; \
	rpmlog="`echo "$$changelog" | sed -e 's/@.*>)/)/' -e 's/(.*</(/'`"; \
	DATELINE="* `date "+%a %b %d %Y"` `hg showconfig ui.username` - $$NEWEXTRAS_VERSION-$(EXTRAS_RELEASE)" ; \
	cl=`grep -n %changelog $(EXTRAS_SPECFILE) | cut -d : -f 1` ; \
	tail --lines=+$$(($$cl + 1)) $(EXTRAS_SPECFILE) > speclog ; \
	(head -n $$cl $(EXTRAS_SPECFILE) ; echo "$$DATELINE" ; echo "$$rpmlog"; echo ""; cat speclog) > $(EXTRAS_SPECFILE).new ; \
	mv $(EXTRAS_SPECFILE).new $(EXTRAS_SPECFILE); rm -f speclog; \
	sed -i "s/Version: $(EXTRAS_VERSION)/Version: $$NEWEXTRAS_VERSION/" $(EXTRAS_SPECFILE); \
	@make changelog

