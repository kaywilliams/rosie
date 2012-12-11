PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/shared
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/shared

clean:
	rm -f *.pyc *.pyo
