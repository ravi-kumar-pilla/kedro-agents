import streamlit as st
import requests
import json
import pandas as pd

st.title("Kedro Notebook Migration Agent")
st.markdown("Upload a Jupyter notebook to analyze its structure and generate Kedro pipeline configuration.")

uploaded_file = st.file_uploader("Upload a Jupyter Notebook", type=["ipynb"])
if uploaded_file is not None:
    files = {"file": uploaded_file.getvalue()}
    with st.spinner("Processing notebook..."):
        res = requests.post("http://localhost:8000/process", files=files)
    
    if res.status_code == 200:
        output = res.json()
        
        # Display cell summaries as a table
        st.subheader("📄 Notebook Cell Analysis")
        try:
            # Handle both dict and JSON string cases
            if isinstance(output["summaries"], dict):
                summaries_data = output["summaries"]
            elif isinstance(output["summaries"], str):
                summaries_data = json.loads(output["summaries"])
            else:
                summaries_data = output["summaries"]
                
            # Handle LLM-based summary format - should be a list of cell analysis objects
            if isinstance(summaries_data, list):
                # Convert to DataFrame for table display
                df = pd.DataFrame(summaries_data)
                
                # Display as an interactive table
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "cell_number": st.column_config.NumberColumn("Cell #", width="small"),
                        "cell_type": st.column_config.TextColumn("Type", width="small"),
                        "source_preview": st.column_config.TextColumn("Source Preview", width="large"),
                        "intent": st.column_config.TextColumn("Cell Intent", width="medium"),
                        "lines_of_code": st.column_config.NumberColumn("Lines", width="small")
                    }
                )
            else:
                st.error("Unexpected summary format")
                st.json(summaries_data)
        except json.JSONDecodeError:
            st.error("Could not parse cell summaries")
            st.text(output["summaries"])
        
        # Display Kedro JSON configuration
        st.subheader("🛠 Kedro Pipeline Configuration")
        try:
            # Handle both dict and JSON string cases
            if isinstance(output["kedro_json"], dict):
                kedro_data = output["kedro_json"]
            elif isinstance(output["kedro_json"], str):
                kedro_data = json.loads(output["kedro_json"])
            else:
                kedro_data = output["kedro_json"]
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Datasets", len(kedro_data.get("datasets", {})))
            with col2:
                st.metric("Nodes", len(kedro_data.get("nodes", [])))
            with col3:
                st.metric("Pipelines", len(kedro_data.get("pipelines", [])))
            
            # Display JSON in expandable sections
            with st.expander("📊 Datasets Configuration", expanded=False):
                if kedro_data.get("datasets"):
                    st.json(kedro_data["datasets"])
                else:
                    st.info("No datasets identified")
            
            with st.expander("⚙️ Nodes Configuration", expanded=False):
                if kedro_data.get("nodes"):
                    st.json(kedro_data["nodes"])
                else:
                    st.info("No processing nodes identified")
            
            with st.expander("🔄 Pipelines Configuration", expanded=False):
                if kedro_data.get("pipelines"):
                    st.json(kedro_data["pipelines"])
                else:
                    st.info("No pipelines created")
            
            # Download option for the JSON
            st.download_button(
                label="📥 Download Kedro Configuration",
                data=json.dumps(kedro_data, indent=2),
                file_name="kedro_config.json",
                mime="application/json"
            )
            
        except json.JSONDecodeError as e:
            st.error(f"Could not parse Kedro JSON: {str(e)}")
            st.text(output["kedro_json"])
    else:
        st.error(f"Error processing notebook. Status code: {res.status_code}")
        if res.text:
            st.text(res.text)
