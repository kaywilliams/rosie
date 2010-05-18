PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/solutionstudio/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/solutionstudio/event

clean:
	rm -f *.pyc *.pyo
