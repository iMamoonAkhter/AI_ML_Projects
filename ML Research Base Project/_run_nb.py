import nbformat
from nbclient import NotebookClient

path = "ML EWS.ipynb"
nb = nbformat.read(path, as_version=4)
for cell in nb.cells:
    if cell.get("cell_type") == "code":
        cell["outputs"] = []
        cell["execution_count"] = None

client = NotebookClient(nb, timeout=1200, kernel_name="python3")
try:
    client.execute()
    status = "SUCCESS"
    err = ""
except Exception as e:
    status = "FAILED"
    err = repr(e)

nbformat.write(nb, path)
print("EXECUTION_STATUS:", status)
if err:
    print("ERROR:", err)
for i, cell in enumerate(nb.cells):
    if cell.get("cell_type") != "code":
        continue
    for out in cell.get("outputs", []):
        if out.get("output_type") == "error":
            print(f"\n--- ERROR in cell index {i} ---")
            print(out.get("ename"), ":", out.get("evalue"))
            print("\n".join(out.get("traceback", []))[:3000])
