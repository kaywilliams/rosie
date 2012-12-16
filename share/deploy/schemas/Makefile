SUBDIRS = repo 

.PHONY: all clean install

all:

install:
	mkdir -p $(DESTDIR)/usr/share/deploy/schemas
	install -pm 644 deploy.rng $(DESTDIR)/usr/share/deploy/schemas/deploy.rng

	for dir in $(SUBDIRS); do make -C $$dir DESTDIR=`cd $(DESTDIR); pwd` install; [ $$? = 0 ] || exit 1; done

clean:
