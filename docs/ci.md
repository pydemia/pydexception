# Continuous integration

The two CI services check different parts of the package:

| Service | Configuration | Runs |
| --- | --- | --- |
| GitHub Actions | `.github/workflows/ci.yml` | Builds the wheel and source distribution on Python 3.12, then installs the wheel in a fresh environment and checks an HTTP response. Runs for pull requests and pushes to `main`. |
| CircleCI | `.circleci/config.yml` | Runs tests, Ruff, and mypy for Python 3.10–3.13 with both minimum and latest supported FastAPI/Pydantic versions (eight jobs). |

To activate the CircleCI workflow, connect the public `pydemia/pydexception` repository using the CircleCI GitHub App. Create a pipeline using the CircleCI configuration file `.circleci/config.yml` and a push trigger for branches. Enable CircleCI GitHub Checks so the compatibility workflow appears on pull requests. After the first successful run, require its check alongside the GitHub Actions package check in the repository's branch rules if both should gate merges.

The configuration does not publish to PyPI. Add a separate release workflow and trusted publisher when a release is ready.
