PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/systemstudio/modules/extensions/repocreate/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/systemstudio/modules/extensions/repocreate

clean:
	rm -f *.pyc *.pyo
