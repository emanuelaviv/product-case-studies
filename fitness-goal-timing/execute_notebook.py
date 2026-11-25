"""Execute the notebook locally in IPython without network sockets."""

import json
import os
import sys
from pathlib import Path
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output

root = Path(__file__).resolve().parent
os.chdir(root)
sys.path.insert(0, str(root))
notebook = nbformat.read(root / "experiment.ipynb", as_version=4)
nbformat.validate(notebook)
shell = InteractiveShell.instance()
count = 0
for cell in notebook.cells:
    if cell.cell_type != "code":
        continue
    count += 1
    with capture_output(display=True) as captured:
        result = shell.run_cell(cell.source, store_history=True)
    if not result.success:
        raise RuntimeError(str(result.error_before_exec or result.error_in_exec))
    cell.execution_count = count
    cell.outputs = []
    for name, text in [("stdout", captured.stdout), ("stderr", captured.stderr)]:
        if text:
            cell.outputs.append(nbformat.v4.new_output("stream", name=name, text=text))
    for output in captured.outputs:
        cell.outputs.append(
            nbformat.v4.new_output("display_data", data=output.data, metadata=output.metadata)
        )
nbformat.validate(notebook)
nbformat.write(notebook, root / "experiment.ipynb")
report = {
    "status": "PASS",
    "executed_code_cells": count,
    "errors": 0,
    "schema": "nbformat 4",
    "execution_method": "Fresh in-process IPython shell, sequential notebook cells; no Jupyter server or socket-based kernel",
    "embedded_chart": any(
        output.get("data", {}).get("image/png")
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.outputs
    ),
}
assert report["embedded_chart"]
(root / "outputs/notebook_validation.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
)
print(json.dumps(report, indent=2))
