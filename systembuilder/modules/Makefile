SUBDIRS = core extensions shared

PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:
	for dir in $(SUBDIRS); do make -C $$dir; done

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/systembuilder/modules
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/systembuilder/modules

	for dir in $(SUBDIRS); do make -C $$dir PYTHONLIBDIR=`cd $(PYTHONLIBDIR); pwd` DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
	rm -f *.pyc *.pyo
	for dir in $(SUBDIRS); do make -C $$dir clean; done
