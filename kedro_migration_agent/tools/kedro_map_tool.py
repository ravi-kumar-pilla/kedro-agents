from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
import nbformat
import json
import ast

def extract_functions_from_cell(source_code):
    """Extract function definitions from a code cell."""
    functions = []
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get function parameters
                params = [arg.arg for arg in node.args.args]
                functions.append({
                    "name": node.name,
                    "parameters": params
                })
    except:
        # Fallback to regex if AST fails
        import re
        func_matches = re.findall(r'def\s+(\w+)\s*\([^)]*\)', source_code)
        for func_name in func_matches:
            functions.append({
                "name": func_name,
                "parameters": []
            })
    return functions

@tool("map_to_kedro_json", return_direct=False)
def map_to_kedro_json(path: str) -> str:
    """Analyze notebook and create Kedro JSON mapping using LLM analysis."""
    try:
        # Clean the path
        path = path.strip().strip('`')
        nb = nbformat.read(path, as_version=4)
        
        # Initialize LLM
        llm = ChatOllama(model="llama3", temperature=0)
        
        # Prepare prompt template for Kedro mapping
        kedro_prompt = PromptTemplate(
            input_variables=["notebook_cells"],
            template="""You are a Kedro expert. Analyze this Jupyter notebook and create a Kedro pipeline configuration.

Notebook cells:
{notebook_cells}

Create a JSON response with:
1. "datasets" - identify data inputs/outputs (CSV, DataFrame variables, etc.)
2. "nodes" - convert functions to Kedro nodes with proper inputs/outputs  
3. "pipelines" - group related nodes into logical pipelines

Return ONLY valid JSON format like:
{{
  "datasets": {{
    "dataset_name": {{
      "type": "pandas.CSVDataSet",
      "filepath": "data/01_raw/dataset_name.csv"
    }}
  }},
  "nodes": [
    {{
      "name": "node_name",
      "func": "function_name", 
      "inputs": ["input_dataset"],
      "outputs": ["output_dataset"]
    }}
  ],
  "pipelines": [
    {{
      "name": "pipeline_name",
      "nodes": ["node_name"]
    }}
  ]
}}"""
        )
        
        # Extract all cells content
        cells_content = ""
        datasets = {}
        nodes = []
        
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == "code" and cell.source.strip():
                cells_content += f"\n\nCell {i}:\n{cell.source}"
                
                # Extract functions for node creation
                functions = extract_functions_from_cell(cell.source)
                for func in functions:
                    # Create node for each function
                    node = {
                        "name": func["name"],
                        "func": func["name"],
                        "inputs": func["parameters"],  # Function parameters become inputs
                        "outputs": [func["name"] + "_output"]  # Function output
                    }
                    nodes.append(node)
                    
                    # Create datasets for function parameters
                    for param in func["parameters"]:
                        datasets[param] = {
                            "type": "pandas.CSVDataset",
                            "filepath": f"data/01_raw/{param}.csv"
                        }
                    
                    # Create output dataset
                    datasets[func["name"] + "_output"] = {
                        "type": "pandas.CSVDataset", 
                        "filepath": f"data/02_processed/{func['name']}_output.csv"
                    }
        
        # If we have manually extracted functions, use that structure
        if nodes:
            kedro_structure = {
                "datasets": datasets,
                "nodes": nodes,
                "pipelines": [
                    {
                        "name": "notebook_pipeline",
                        "nodes": [node["name"] for node in nodes]
                    }
                ]
            }
            return json.dumps(kedro_structure, indent=2, ensure_ascii=False)
        
        # Otherwise use LLM analysis
        try:
            formatted_prompt = kedro_prompt.format(notebook_cells=cells_content)
            response = llm.invoke(formatted_prompt)
            
            # Try to extract JSON from response
            response_text = response.content.strip()
            
            # Find JSON block in response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                # Find first { and last }
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
            
            # Validate JSON
            parsed_json = json.loads(json_text)
            return json.dumps(parsed_json, indent=2, ensure_ascii=False)
            
        except Exception as llm_error:
            # Fallback structure
            return json.dumps({
                "datasets": {
                    "raw_data": {
                        "type": "pandas.CSVDataset",
                        "filepath": "data/01_raw/raw_data.csv"
                    }
                },
                "nodes": [
                    {
                        "name": "process_data",
                        "func": "process_data",
                        "inputs": ["raw_data"],
                        "outputs": ["processed_data"]
                    }
                ],
                "pipelines": [
                    {
                        "name": "data_pipeline",
                        "nodes": ["process_data"]
                    }
                ],
                "llm_error": str(llm_error)
            }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"Error creating Kedro mapping: {str(e)}"}, indent=2)