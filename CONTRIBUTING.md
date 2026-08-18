# Contributing

Branches use `feature/DAR-123-short-name`, `fix/DAR-123-short-name`, or `chore/short-name`. Open a pull request into `develop`; releases merge from `develop` into `main`.

Every PR must pass Ruff, mypy, pytest with coverage, the migration check, dependency audit, and secret scan. Configure GitHub branch protection on `main` and `develop` to require these status checks, prevent direct pushes, and require at least one approving review. Never commit `.env`, credentials, tokens, or production data.
