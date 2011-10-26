PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/centosstudio/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/centosstudio/locals

clean:
	rm -f *.pyc *.pyo
