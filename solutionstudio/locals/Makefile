PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/solutionstudio/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/solutionstudio/locals

clean:
	rm -f *.pyc *.pyo
