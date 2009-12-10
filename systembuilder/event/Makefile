PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/event

clean:
	rm -f *.pyc *.pyo
