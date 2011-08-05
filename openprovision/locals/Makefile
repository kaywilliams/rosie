PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/locals

clean:
	rm -f *.pyc *.pyo
