PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/modules/core/rpmbuild
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/modules/core/rpmbuild

clean:
	rm -f *.pyc *.pyo
