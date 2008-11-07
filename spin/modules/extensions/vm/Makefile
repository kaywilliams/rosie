PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/vm/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions/vm

clean:
	rm -f *.pyc *.pyo
