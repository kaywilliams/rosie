all: repos

repos:
	buildrepos --config-file pkglist-test-repos1.xml \
	--repo-file pkglist-test-repos1.repo; \
	buildrepos --config-file pkglist-test-repos2.xml \
	--repo-file pkglist-test-repos2.repo; \
	buildrepos --config-file pkglist-test-repos3.xml \
	--repo-file pkglist-test-repos3.repo

clean:
	rm -rf repo1; rm -rf repo2; rm -rf repo3; rm -f pkglist-test-*.repo