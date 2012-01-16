PKGNAME := centosstudio
SPECFILE := $(PKGNAME).spec
VERSION := $(shell awk '/Version:/ { print $$2 }' $(SPECFILE))
RELEASE := $(shell awk '/Release:/ { print $$2 }' $(SPECFILE) | sed -e 's|%{?dist}||g')

SUBDIRS = bin docsrc/man etc share centosstudio

BUILDARGS =

define COMPILE_PYTHON
	python -c "import compileall as C; C.compile_dir('$(1)', force=1)"
	python -O -c "import compileall as C; C.compile_dir('$(1)', force=1)"
endef

.PHONY: all clean install tag archive srpm 

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
		hg tag -f --user "$(USERNAME)" -m "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE); \
	else \
		hg tag -f -m "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)" $(PKGNAME)-$(VERSION)-$(RELEASE); \
	fi
	@echo "Tagged as $(PKGNAME)-$(VERSION)-$(RELEASE)"

archive: tag
	@hg archive -t tgz --prefix=$(PKGNAME)-$(VERSION) \
        $(PKGNAME)-$(VERSION).tar.gz

srpm: archive
	@rpmbuild $(BUILDARGS) -ts $(PKGNAME)-$(VERSION).tar.gz  || exit 1
	@rm -f $(PKGNAME)-$(VERSION).tar.gz

