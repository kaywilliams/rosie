all: repos

repos:
	buildrepos --config-file download-test-repos.xml \
	--repo-file download-test-repos.repo

clean:
	rm -rf repo1; rm -rf repo2; rm -f download-test-repos.repo