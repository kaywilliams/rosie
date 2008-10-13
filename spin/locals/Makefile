PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/locals
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/locals
	../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/locals $(PYFILES)

clean:
	rm -f *.pyc *.pyo
