PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/modules/extensions/repocreate/
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/modules/extensions/repocreate

clean:
	rm -f *.pyc *.pyo
