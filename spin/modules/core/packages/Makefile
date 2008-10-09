PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/packages/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/packages
	../../../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/packages $(PYFILES)

clean:
	rm -f *.pyc *.pyo
