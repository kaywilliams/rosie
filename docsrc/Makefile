SUBDIRS = man

all:
	for dir in $(SUBDIRS); do make -C $$dir; done

install:
	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
	for dir in $(SUBDIRS); do make -C $$dir clean; done
