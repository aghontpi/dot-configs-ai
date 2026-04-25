---
name: ipynb-editor
description: Edit .ipynb Jupyter notebook files directly. Use this skill when you need to modify the contents of a .ipynb file, which is otherwise restricted from standard file editing tools. It provides a black-box script to find and replace text safely in the notebook.
---

# Ipynb Editor

## Overview

Since standard file editing tools are restricted from directly modifying `.ipynb` files, this skill provides a reliable Python script to update code within a Jupyter Notebook safely. It acts as a black box: you don't need to manually parse the JSON, find cell indices, or use temporary files.

## Workflow: Updating a Notebook

When the user asks you to edit a `.ipynb` file, follow these steps:

### The Black Box Approach

Use the `run_command` tool to execute the `update_ipynb.py` script. Pass the text you want to find and the text you want to replace it with as environment variables (`FIND` and `REPLACE`).

This will automatically search through all cells and safely perform the replacement, preserving the `.ipynb` structure. 

**DO NOT** create temporary files, and **DO NOT** try to manually query the notebook with `jq`.

```bash
# Example usage:
FIND="old_variable = 1" REPLACE="new_variable = 2" python3 skills/ipynb-editor/scripts/update_ipynb.py --file path/to/notebook.ipynb
```

### Multi-line Replacements

If you need to perform a multi-line replacement, you can export the environment variables first, or use bash string literals:

```bash
export FIND="def old_func():
    pass"

export REPLACE="def new_func():
    print('hello')
    pass"

python3 skills/ipynb-editor/scripts/update_ipynb.py --file path/to/notebook.ipynb
```

Alternatively, you can still use the legacy mode if you need to replace a cell entirely by passing `--cell <index>` and `--source <temp_file.py>`. But the environment variable approach is preferred for simple edits.
