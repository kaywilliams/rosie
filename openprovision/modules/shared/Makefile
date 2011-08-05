PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/modules/shared
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/modules/shared

clean:
	rm -f *.pyc *.pyo
