.PHONY: all install clean

all:

install:
	mkdir -p $(DESTDIR)/etc/logrotate.d
	install -pm 644 deploy $(DESTDIR)/etc/logrotate.d/deploy

clean:
