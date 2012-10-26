PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/event
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/repostudio/event

clean:
	rm -f *.pyc *.pyo
