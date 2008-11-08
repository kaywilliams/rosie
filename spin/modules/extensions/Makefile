SUBDIRS = installer repocreate vm

PYFILES = $(wildcard *.py)

.PHONY: all clean install

all:
	for dir in $(SUBDIRS); do make -C $$dir; done

install:
	mkdir -p $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions
	cp -var $(PYFILES) $(DESTDIR)/$(PYTHONLIBDIR)/spin/modules/extensions

	for dir in $(SUBDIRS); do make -C $$dir PYTHONLIBDIR=`cd $(PYTHONLIBDIR); pwd` DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
	rm -f *.pyc *.pyo
	for dir in $(SUBDIRS); do make -C $$dir clean; done
