SUBDIRS = repo 

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/repostudio/schemas
	install -pm 644 repostudio.rng $(DESTDIR)/usr/share/repostudio/schemas/repostudio.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
