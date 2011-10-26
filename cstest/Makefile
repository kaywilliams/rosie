SUBDIRS = modules/download modules/depsolve

all:
	for d in $(SUBDIRS); do make -C $$d; done
clean:
	for d in $(SUBDIRS); do make -C $$d clean; done
