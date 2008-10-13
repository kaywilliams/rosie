PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/installer
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/installer
	../../../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/installer $(PYFILES)

clean:
	rm -f *.pyc *.pyo
