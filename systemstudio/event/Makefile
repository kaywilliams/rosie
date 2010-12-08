PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/systemstudio/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/systemstudio/event

clean:
	rm -f *.pyc *.pyo
