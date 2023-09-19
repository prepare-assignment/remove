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

`force` will exit with an error if any of the inputs doesn't match any files/directories.  
`recursive` will exit with an error if any of the inputs match a directory.