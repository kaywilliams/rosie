PKGNAME := systembuilder
SPECFILE := $(PKGNAME).spec
VERSION := $(shell awk '/Version:/ { print $$2 }' $(SPECFILE))
RELEASE := $(shell awk '/Release:/ { print $$2 }' $(SPECFILE) | sed -e 's|%{?dist}||g')

SUBDIRS = bin docsrc etc share systembuilder

BUILDARGS =

define COMPILE_PYTHON
	python -c "import compileall as C; C.compile_dir('$(1)', force=1)"
	python -O -c "import compileall as C; C.compile_dir('$(1)', force=1)"
endef

.PHONY: all clean install tag changelog archive srpm bumpver

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
	$(call COMPILE_PYTHON,$(DESTDIR)/$(PYTHONLIBDIR))

tag:
	@if [ "$(USERNAME)" != "" ]; then \
		hg tag --user "$(USERNAME)" -m "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE); \
	else \
		hg tag -m "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE); \
	fi
	@echo "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)"

changelog:
	@hg log --style changelog > ChangeLog

archive: tag
	@hg archive --exclude systembuilder-enterprise.spec \
                    --exclude Makefile.enterprise \
		    -t tgz --prefix=$(PKGNAME)-$(VERSION) $(PKGNAME)-$(VERSION).tar.gz

srpm: archive
	@rpmbuild $(BUILDARGS) -ts $(PKGNAME)-$(VERSION).tar.gz  || exit 1
	@rm -f $(PKGNAME)-$(VERSION).tar.gz

bumpver:
	@NEWSUBVER=$$((`echo $(VERSION) | cut -d . -f 3` + 1)) ; \
	NEWVERSION=`echo $(VERSION).$$NEWSUBVER |cut -d . -f 1-2,4` ; \
	changelog="`hg log --exclude systembuilder-enterprise.spec --exclude .hgtags --exclude systembuilder.spec --exclude ChangeLog --exclude Makefile --exclude Makefile.enterprise -r tip:$(PKGNAME)-$(VERSION)-$(RELEASE) --template "- {desc|strip|firstline} ({author})\n" 2> /dev/null || echo "- Initial Build"`"; \
	rpmlog="`echo "$$changelog" | sed -e 's/@.*>)/)/' -e 's/(.*</(/'`"; \
	DATELINE="* `date "+%a %b %d %Y"` `hg showconfig ui.username` - $$NEWVERSION-$(RELEASE)" ; \
	cl=`grep -n %changelog $(SPECFILE) | cut -d : -f 1` ; \
	tail --lines=+$$(($$cl + 1)) $(SPECFILE) > speclog ; \
	(head -n $$cl $(SPECFILE) ; echo "$$DATELINE" ; echo "$$rpmlog"; echo ""; cat speclog) > $(SPECFILE).new ; \
	mv $(SPECFILE).new $(SPECFILE); rm -f speclog; \
	sed -i "s/Version: $(VERSION)/Version: $$NEWVERSION/" $(SPECFILE)
	make changelog
