PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/centosstudio/modules/extensions/installer/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/centosstudio/modules/extensions/installer

clean:
	rm -f *.pyc *.pyo
