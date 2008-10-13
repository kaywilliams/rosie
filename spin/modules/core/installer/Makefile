PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/installer
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/installer
	../../../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/installer $(PYFILES)

clean:
	rm -f *.pyc *.pyo
