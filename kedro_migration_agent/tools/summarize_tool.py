from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
import nbformat
import json

@tool("summarize_cells", return_direct=False)
def summarize_cells(path: str) -> str:
    """Summarize each cell in a Jupyter notebook using LLM analysis."""
    try:
        # Clean the path to remove any whitespace/newlines/backticks
        path = path.strip().strip('`')
        nb = nbformat.read(path, as_version=4)
        
        # Initialize LLM
        llm = ChatOllama(model="llama3", temperature=0)
        
        # Create prompt template
        prompt = PromptTemplate(
            input_variables=["cell_code", "cell_type"],
            template="""Analyze this {cell_type} cell and explain its intent/purpose in 1-2 sentences:

```
{cell_code}
```

Focus on what the code accomplishes, not implementation details."""
        )
        
        cell_summaries = []
        
        for i, cell in enumerate(nb.cells):
            cell_info = {
                "cell_number": i,
                "cell_type": cell.cell_type,
                "source_preview": cell.source[:150] + "..." if len(cell.source) > 150 else cell.source,
                "lines_of_code": len(cell.source.split('\n')) if cell.source.strip() else 0
            }
            
            # Get LLM analysis for non-empty cells
            if cell.source.strip():
                try:
                    formatted_prompt = prompt.format(
                        cell_code=cell.source,
                        cell_type=cell.cell_type
                    )
                    response = llm.invoke(formatted_prompt)
                    cell_info["intent"] = response.content.strip()
                except Exception as e:
                    cell_info["intent"] = f"Analysis failed: {str(e)[:50]}"
            else:
                cell_info["intent"] = "Empty cell"
            
            cell_summaries.append(cell_info)
        
        return json.dumps(cell_summaries, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Error processing notebook: {str(e)}"}, indent=2)
