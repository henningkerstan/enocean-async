# Versioning

This project uses [Semantic Versioning](https://semver.org/) with a dev pre-release stage, managed by [bump-my-version](https://callowayproject.github.io/bump-my-version/).

## Version format

| Format | Meaning |
|--------|---------|
| `1.2.3` | Released version |
| `1.2.4-dev0` | Development snapshot |
| `1.2.4-devN` | N commits past the last dev tag |

The dev number increments automatically with each commit — no manual action needed between bumps.

## Workflow

### Starting a new development cycle

After a release, or when beginning work on the next version, decide on the version family and bump accordingly:

```bash
bump-my-version bump patch  # creates version 1.2.4-dev0, next version will be 1.2.4
bump-my-version bump minor  # next will be 1.3.0
bump-my-version bump major  # next will be 2.0.0
```

This updates version files and commits. No tag is created for dev versions — only the final release is tagged. The dev number then advances automatically with every subsequent commit.

### Releasing

When the code is ready to release:

```bash
bump-my-version bump pre_l --tag
```

This promotes the current dev version to a release (e.g. `1.2.4-dev3` → `1.2.4`), updates version files, commits, and creates a `v1.2.4` tag.

### Checking the current version

```bash
bump-my-version show current_version
```

### Previewing what a bump would produce

```bash
bump-my-version show-bump
```

## `--tag` flag

By default (`tag = false` in `pyproject.toml`), `bump` never creates a git tag. The `--tag` flag opts in.

| Command | Tag? | Reason |
|---------|------|--------|
| `bump patch` | No | Dev snapshots don't need tags |
| `bump minor` | No | Same |
| `bump major` | No | Same |
| `bump pre_l --tag` | **Yes** | This is the release — tag is the artifact |

If you accidentally omit `--tag` on a release, create the tag manually with `git tag v1.2.4 && git push origin v1.2.4`.

## Rules of thumb

- **Never edit the version manually** in `pyproject.toml` or `__init__.py` — always use `bump-my-version`.
- **Unsure whether it's patch, minor, or major?** Start with `bump patch`. You can always re-bump before the release if the scope grows.
- **Only `bump pre_l --tag` produces a release tag** — all other bumps are untagged by default.
