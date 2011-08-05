all: test-repos.repo

test-repos.repo: test-repos.xml
	buildrepos --config-file test-repos.xml \
	--repo-file test-repos.repo

clean:
	rm -rf repo1; rm -rf repo2; rm -f test-repos.repo
