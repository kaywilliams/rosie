PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/deploy/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/deploy/event

clean:
	rm -f *.pyc *.pyo
