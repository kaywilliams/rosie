PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/vm/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/core/vm

clean:
	rm -f *.pyc *.pyo
