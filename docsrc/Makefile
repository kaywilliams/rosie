DOCGEN=../tools/docgen
all: spin.conf.5.gz distro.conf.5.gz

spin.conf.5.gz:
	$(DOCGEN) --xml-dir ./ --glob 'spin.rng' --output ./spin.conf.5.gz

distro.conf.5.gz:
	$(DOCGEN) --xml-dir ./ --glob '*rng' --nglob 'spin.rng' --output ./distro.conf.5.gz

