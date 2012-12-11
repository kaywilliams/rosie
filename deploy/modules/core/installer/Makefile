PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/core/installer
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/core/installer

clean:
	rm -f *.pyc *.pyo
