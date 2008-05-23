all : pkglist-test-repos1.repo pkglist-test-repos2.repo pkglist-test-repos3.repo pkglist-test-repos4.repo

pkglist-test-repos1.repo: pkglist-test-repos1.xml
	buildrepos --config-file pkglist-test-repos1.xml \
	--repo-file pkglist-test-repos1.repo

pkglist-test-repos2.repo: pkglist-test-repos2.xml
	buildrepos --config-file pkglist-test-repos2.xml \
	--repo-file pkglist-test-repos2.repo

pkglist-test-repos3.repo: pkglist-test-repos3.xml
	buildrepos --config-file pkglist-test-repos3.xml \
	--repo-file pkglist-test-repos3.repo

pkglist-test-repos4.repo: pkglist-test-repos4.xml
	buildrepos --config-file pkglist-test-repos4.xml \
	--repo-file pkglist-test-repos4.repo

clean :
	rm -rf repo1; rm -rf repo2; rm -rf repo3; \
	rm -rf repo4; rm -f pkglist-test-*.repo
