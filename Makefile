PKGNAME := spin
SPECFILE := $(PKGNAME).spec
VERSION := $(shell awk '/Version:/ { print $$2 }' $(SPECFILE))
RELEASE := $(shell awk '/Release:/ { print $$2 }' $(SPECFILE) | sed -e 's|%{?dist}||g')

SUBDIRS = docsrc etc

BUILDARGS =

.PHONY: all clean depend subdirs build install tag changelog archive srpm bumpver

all: build

clean:
	@rm -rf build/

depend: build subdirs

subdirs:
	for dir in $(SUBDIRS); do make -C $$dir; done

build:
	python setup.py build

install:
	@if [ "$(DESTDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A destdir is required"; \
		exit 1; \
	fi
	python setup.py install -O1 --skip-build --root $(DESTDIR) --record=INSTALLED_FILES
	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

tag:
	@hg tag -m "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE)
	@echo "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)"

changelog:
	@hg log --style changelog > ChangeLog

archive:
	@hg archive -t tar --prefix=$(PKGNAME)-$(VERSION) $(PKGNAME)-$(VERSION).tar
	@gzip $(PKGNAME)-$(VERSION).tar

srpm: archive
	@rpmbuild $(BUILDARGS) -ts $(PKGNAME)-$(VERSION).tar.gz  || exit 1
	@rm -f $(PKGNAME)-$(VERSION).tar.gz

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
	sed -i "s/version = '$(VERSION)'/version = '"$$NEWVERSION"'/" setup.py
	@make changelog
