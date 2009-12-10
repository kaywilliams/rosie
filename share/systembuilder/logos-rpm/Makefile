SUBDIRS = files fonts icons

.PHONY: all clean install

all:
	for dir in $(SUBDIRS); do make -C $$dir; done

install:
	mkdir -p $(DESTDIR)/usr/share/spin/logos-rpm
	install -pm 644 centos5.xml $(DESTDIR)/usr/share/spin/logos-rpm/centos5.xml
	install -pm 644 common.xml  $(DESTDIR)/usr/share/spin/logos-rpm/common.xml
	install -pm 644 fedora9.xml $(DESTDIR)/usr/share/spin/logos-rpm/fedora9.xml
	install -pm 644 icons.xml $(DESTDIR)/usr/share/spin/logos-rpm/icons.xml
	install -pm 644 redhat5.xml $(DESTDIR)/usr/share/spin/logos-rpm/redhat5.xml

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
	for dir in $(SUBDIRS); do make -C $$dir clean; done
