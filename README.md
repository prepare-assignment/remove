# Remove action

This action removes files/directories. The action is modeled after the linux `rm` command.
For more information see the [man page](https://man7.org/linux/man-pages/man1/rm.1.html).

## Options

The following options are available:

```yaml
input:
  description: "Files (glob) to remove"
  required: true
  type: "array"
  items: "string"
force:
  description: "Ignore nonexistent files and arguments"
  type: boolean
  default: false
recursive:
  description: "Whether to recursively remove all subdirectories"  type: boolean
  default: false
```

- `force`: if false and an input doesn't match any files, it will fail the action
- `recursive`: if false and an input is a directory, it will fail the action

## Outputs

The following outputs are available:

```yaml
files:
  description: Matched globs that have been removed
  type: array
  items: string
```

`files`: contains an array of all the inputs that have been removed.

* > :warning: If a directory is removed, it will only list the matched directory path, not all sub files/directories.

## Releases

Releases are automated with [semantic-release](https://semantic-release.gitbook.io/). Pull requests are squash merged, so the PR title becomes the commit on `main` and must follow [Conventional Commits](https://www.conventionalcommits.org/) (checked on every PR):

| PR title | Release |
|----------|---------|
| `fix: ...`, `perf: ...` | patch (1.2.3 → 1.2.4) |
| `feat: ...` | minor (1.2.3 → 1.3.0) |
| `!` after the type (e.g. `feat!: ...`, `refactor!: ...`) or a `BREAKING CHANGE:` footer | major (1.2.3 → 2.0.0) |
| `docs:`, `chore:`, `ci:`, `build:`, `refactor:`, `test:`, `style:`, `revert:` | no release |

On every merge to `main` the next version is determined, tagged (`vX.Y.Z`) and a GitHub release is created. The major tag (e.g. `v1`) is moved to the new release, so `uses: remove@v1` always gets the newest 1.x version.

Because the major tag moves, `git pull` in an existing clone can fail with `! [rejected] v1 -> v1 (would clobber existing tag)`. Update the tags once with `git fetch --tags --force` and pull again.
