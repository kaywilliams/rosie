PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/repocreate/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/repocreate

clean:
	rm -f *.pyc *.pyo
