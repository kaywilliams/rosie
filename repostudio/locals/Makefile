PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/locals

clean:
	rm -f *.pyc *.pyo
