PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/openprovision/event

clean:
	rm -f *.pyc *.pyo
