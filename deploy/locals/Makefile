PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/deploy/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/deploy/locals

clean:
	rm -f *.pyc *.pyo
