## v0.1.0rc2 (2025-08-17)

### Feat

- add the save command to create layout files

### Fix

- fix an error about percentages on empty workspaces

## v0.1.0rc1 (2025-08-03)

### BREAKING CHANGE

- The behavior on non-empty workspaces has changed.
- Breaks configurations that contain both
`focused_workspace` and `workspaces`.

### Feat

- map existing windows before applying the layout
- validate regexps before applying the layout
- add a new field `focus` to the layout file
- only allow either `focused_workspace` or `workspaces` to be present
