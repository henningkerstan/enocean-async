Generate release notes for the upcoming release.

Steps:
1. Run `bump-my-version show current_version` to get the current dev version.
2. Run `git log --oneline $(git describe --tags --abbrev=0)..HEAD` to get all commits since the last release tag. If there is no previous tag, use `git log --oneline`.
3. Read `CHANGELOG.md` if it exists to understand the existing format and style.
4. Analyse the commits: group them into meaningful categories such as **New features**, **Bug fixes**, **Breaking changes**, **Internal / maintenance** — omit any category that has no entries. Exclude version-bump commits (messages matching "Bump version:").
5. Write the release notes as a markdown section:

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

Use the version number from step 1 (without the `-devN` suffix, since these notes are for the release). Use today's date.

6. Present the release notes to the user for review. Ask whether to:
   a. Prepend them to `CHANGELOG.md` (create the file if it does not exist), or
   b. Just display them for manual use.
