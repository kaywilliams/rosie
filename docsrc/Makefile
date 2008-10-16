SUBDIRS = man ADFR

.PHONY: all clean html install pdf

all:
	for dir in $(SUBDIRS); do make -C $$dir; done

install:
	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
	for dir in $(SUBDIRS); do make -C $$dir clean; done

html:
	for dir in $(SUBDIRS); do make -C $$dir html; [ $$? = 0 ] || exit 1; done

pdf:
	for dir in $(SUBDIRS); do make -C $$dir pdf; [ $$? = 0 ] || exit 1; done
