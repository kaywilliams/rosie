PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/shared
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/shared
	../../../pycompile --basedir $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/shared $(PYFILES)

clean:
	rm -f *.pyc *.pyo
