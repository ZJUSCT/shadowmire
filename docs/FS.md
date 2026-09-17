# Filesystem constraints

Project names and distribution filenames must not exceed 240 bytes in the
filesystem encoding. The same limit applies to decoded download path components.
If any upstream release exceeds this limit, the entire project is removed
locally and marked as not found upstream. This check applies before file filters,
including when only metadata is synced. Regular syncs do not retry marked projects,
even if their upstream serial changes.
