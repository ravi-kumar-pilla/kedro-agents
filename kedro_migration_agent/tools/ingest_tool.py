from langchain.tools import tool
import nbformat
import json

@tool("load_notebook", return_direct=False)
def load_notebook(path: str) -> str:
    """Load a Jupyter notebook and return cell-by-cell data as JSON."""
    try:
        # Clean the path to remove any whitespace/newlines/backticks
        path = path.strip().strip('`')
        nb = nbformat.read(path, as_version=4)
        
        cells_data = []
        for i, cell in enumerate(nb.cells):
            cell_info = {
                "cell_number": i,
                "cell_type": cell.cell_type,
                "source_code": cell.source,
                "lines_of_code": len(cell.source.split('\n')) if cell.source.strip() else 0,
                "is_empty": not bool(cell.source.strip())
            }
            cells_data.append(cell_info)
        
        return json.dumps(cells_data, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Error loading notebook: {str(e)}"}, indent=2)
