PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/packages/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/packages
	../../../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/packages $(PYFILES)

clean:
	rm -f *.pyc *.pyo
