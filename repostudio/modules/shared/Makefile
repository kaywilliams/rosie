PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/modules/shared
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/modules/shared

clean:
	rm -f *.pyc *.pyo
