PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/event
	../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/event $(PYFILES)

clean:
	rm -f *.pyc *.pyo
