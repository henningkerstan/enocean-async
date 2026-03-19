Prepare the project for a new release: generate release notes, update README and docs, and optionally commit.

Steps:
1. Run `bump-my-version show current_version` to get the current dev version.
2. Run `git log --oneline $(git describe --tags --abbrev=0)..HEAD` to get all commits since the last release tag. If there is no previous tag, use `git log --oneline`.
3. Read `CHANGELOG.md` if it exists to understand the existing format and style.
4. Analyse the commits: group them into meaningful categories such as **New features**, **Bug fixes**, **Breaking changes**, **Internal / maintenance** — omit any category that has no entries. Exclude version-bump commits (messages matching "Bump version:").
5. Draft the release notes as a markdown section:

```
## [version] — YYYY-MM-DD

### Breaking changes
- …

### New features
- …

### Bug fixes
- …

### Internal / maintenance
- …
```

Use the version number from step 1 (without the `-devN` suffix). Use today's date.

6. Review and update documentation:
   a. Read `README.md` and update it if the release contains user-visible changes (new features, changed APIs, new examples, updated requirements).
   b. Read any relevant docs files (e.g. `ARCHITECTURE.md`, `HOMEASSISTANT.md`) and update sections that are affected by the changes in this release.
   c. Present a summary of all proposed doc changes to the user before writing anything.

7. Present the release notes to the user for review. Ask whether to:
   a. Prepend them to `CHANGELOG.md` (create the file if it does not exist) and write the doc updates, or
   b. Just display them for manual use.
