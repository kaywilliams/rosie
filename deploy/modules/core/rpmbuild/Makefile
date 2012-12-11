PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/core/rpmbuild
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/core/rpmbuild

clean:
	rm -f *.pyc *.pyo
