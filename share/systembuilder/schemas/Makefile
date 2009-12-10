SUBDIRS = appliance logos-rpm

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/spin/schemas
	install -pm 644 spin.rng $(DESTDIR)/usr/share/spin/schemas/spin.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
