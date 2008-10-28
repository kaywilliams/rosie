PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/locals

clean:
	rm -f *.pyc *.pyo
