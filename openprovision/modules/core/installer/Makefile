PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/modules/core/installer
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/modules/core/installer

clean:
	rm -f *.pyc *.pyo
