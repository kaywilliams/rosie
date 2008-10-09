PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/rpmbuild
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/rpmbuild
	../../../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/rpmbuild $(PYFILES)

clean:
	rm -f *.pyc *.pyo
