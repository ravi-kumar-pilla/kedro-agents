from langchain.agents import initialize_agent, AgentType
from langchain_ollama import ChatOllama
from tools.ingest_tool import load_notebook
from tools.summarize_tool import summarize_cells
from tools.kedro_map_tool import map_to_kedro_json
import tempfile
import json

class KedroMigrationAgent:
    def __init__(self):
        self.llm = ChatOllama(model="llama3", temperature = 0)
        self.tools = [
            load_notebook,
            summarize_cells,
            map_to_kedro_json
        ]
        self.agent = initialize_agent(self.tools, self.llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True, handle_parsing_errors=True)
  
    def run(self, notebook_bytes: bytes):
        import os
        
        # Create temporary file
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".ipynb")
        
        try:
            # Write the notebook data and ensure it's flushed to disk
            with os.fdopen(tmp_fd, 'wb') as tmp_file:
                tmp_file.write(notebook_bytes)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Force write to disk
            
            # Verify file exists and is readable
            if not os.path.exists(tmp_path):
                return {"summaries": json.dumps({"error": "Failed to create temporary file"}, indent=2), 
                       "kedro_json": json.dumps({"error": "Failed to create temporary file"}, indent=2)}
            
            # Call tools directly to get raw JSON outputs
            try:
                summaries = summarize_cells.run(tmp_path)
            except Exception as e:
                summaries = json.dumps({"error": f"Summarization failed: {str(e)}"}, indent=2)
            
            try:
                kedro_json = map_to_kedro_json.run(tmp_path)
            except Exception as e:
                kedro_json = json.dumps({"error": f"Kedro mapping failed: {str(e)}"}, indent=2)
            
            return {"summaries": summaries, "kedro_json": kedro_json}
            
        except Exception as e:
            return {"summaries": json.dumps({"error": f"Agent execution failed: {str(e)}"}, indent=2), 
                   "kedro_json": json.dumps({"error": f"Agent execution failed: {str(e)}"}, indent=2)}
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass  # Ignore cleanup errors

kedro_agent = KedroMigrationAgent()
