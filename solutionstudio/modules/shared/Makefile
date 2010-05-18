PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/systembuilder/modules/shared
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/systembuilder/modules/shared

clean:
	rm -f *.pyc *.pyo
