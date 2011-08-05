PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/modules/core/repocreate/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/modules/core/repocreate

clean:
	rm -f *.pyc *.pyo
