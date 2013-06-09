PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/extensions/installer/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/deploy/modules/extensions/installer

clean:
	rm -f *.pyc *.pyo
