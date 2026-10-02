# Releasing and the Docker image

How a change becomes a GitHub release and a Docker image. Useful for maintainers and for forks.

## What GitHub builds

[`.github/workflows/docker.yml`](../.github/workflows/docker.yml) runs on every push and pull request:

1. **test**: the app and platform test suites (Python 3.13, no network).
2. **image** (pushes and tags only, after the tests pass): builds the app image for `linux/amd64` and
   `linux/arm64` with Docker Buildx and pushes it to the GitHub Container Registry:

| Event | Image tags |
|---|---|
| push to `main` | `latest`, `sha-<commit>` |
| tag `v1.2.3` | `1.2.3`, `1.2`, `sha-<commit>` |
| pull request | none (tests only) |

The workflow logs in with the built-in `GITHUB_TOKEN` (`packages: write`): no secret to configure.

## Make a release

```bash
git tag -a v1.2.0 -m "v1.2.0"
git push origin v1.2.0
```

Then, optionally, `gh release create v1.2.0 --generate-notes`. Users on `:1.2` get it with
`./jobagent update`; users on `:latest` already had it from `main`.

Versioning: `MAJOR.MINOR.PATCH`. Database changes are applied automatically at start-up, so an
upgrade never needs a manual step; say so in the release notes if one ever does.

## In a fork

The workflow pushes to `ghcr.io/<your account>/swiss-job-agent`. After the first build:

1. GitHub → your profile → **Packages** → `swiss-job-agent` → **Package settings**: set the visibility
   to **Public** if others should pull it without logging in, and check it is linked to the repository.
2. Point users at your image: `IMAGE=ghcr.io/<you>/swiss-job-agent:latest` in `.env`, and
   `JOBAGENT_RAW=https://raw.githubusercontent.com/<you>/swiss-job-agent/main` for `./jobagent init`.

Pushing a change to a workflow file needs a token with the `workflow` scope
(`gh auth refresh -s workflow` for the GitHub CLI).

## Checking a build

```bash
gh run list --workflow docker-image
gh run watch
docker pull ghcr.io/nigifabio/swiss-job-agent:latest
docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' ghcr.io/nigifabio/swiss-job-agent:latest
```
