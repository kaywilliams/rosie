PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/solutionstudio/modules/extensions/installer
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/solutionstudio/modules/extensions/installer

clean:
	rm -f *.pyc *.pyo
