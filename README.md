# Remove action

This action removes files/folders. The action is modeled after the linux `mv` command.
For more information see the [man page](https://man7.org/linux/man-pages/man1/rm.1.html).

## Options

The following options are available.

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
    description: "Whether to recursively remove all subdirectories"
    type: boolean
    default: false
```

`force`: if false and an input doesn't match any files, it will fail the action
`recursive`: if false and an input is a directory, it will fail the action

## Outputs

The following outputs are available.

```yaml
outputs:
    files:
        description: Matched globs that have been removed
        type: array
        items: string
```

`files`: contains an array of all the inputs that have been removed.

* > :warning: If a directory is removed, it will only list the matched directory path, not all sub files/directories.