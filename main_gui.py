import streamlit as st
import pandas as pd
import os
from pathlib import Path
from st_aggrid import AgGrid, GridOptionsBuilder

# New Backend Import
try:
    from backend.processing import SAPDataConverter
except ImportError as e:
    st.error(f"Critical Error: Backend module not found. {e}")
    st.stop()

# --- CONSTANTS ---
INPUT_PATH = Path("data/input")
OUTPUT_PATH = Path("data/output")
MAPPING_XLSX = Path("data/mappings/Opdracht_mappingtabellen_ZH01.xlsx")

# --- APP CONFIG ---
st.set_page_config(page_title="SAP Migration Interface", layout="wide", page_icon="🏥")

def init_ui():
    """Initializes the main UI components."""
    st.title("🏥 System Migration Tool: Legacy -> SAP")
    
    # Ensure directories exist
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    tab_convert, tab_map = st.tabs(["🚀 Execute Conversion", "🛠️ Mapping Configuration"])
    
    with tab_convert:
        render_conversion_tab()
    
    with tab_map:
        render_mapping_tab()

def render_conversion_tab():
    st.header("Data Conversion Process")
    
    if not INPUT_PATH.exists():
        st.warning(f"Directory '{INPUT_PATH}' does not exist. Please create it.")
        return

    files = [f.name for f in INPUT_PATH.iterdir() if f.suffix.lower() in ('.xlsx', '.csv')]
    
    if not files:
        st.info("No source files found in input directory.")
        return

    selected_file = st.selectbox("Select Source File:", files)
    preview_rows = st.number_input("Preview Rows:", min_value=1, max_value=1000, value=10)

    if st.button("Run Transformation"):
        _run_transformation_process(selected_file, preview_rows)

def _run_transformation_process(filename, n_rows):
    converter = SAPDataConverter(settings_file='settings.json')
    full_path = str(INPUT_PATH / filename)

    with st.spinner('Processing data...'):
        try:
            result_df = converter.run(full_path)
            
            if result_df.empty:
                st.error("Conversion resulted in empty dataset. Check logs/rules.")
            else:
                st.success(f"Success! Generated {len(result_df)} records.")
                st.dataframe(result_df.head(n_rows))
                
                # Download
                csv_data = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="💾 Download Result",
                    data=csv_data,
                    file_name="SAP_Upload_Data.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Conversion Failed: {e}")
            with st.expander("Debug Details"):
                st.exception(e)

def render_mapping_tab():
    st.header("Edit Mapping Rules")
    
    if not MAPPING_XLSX.exists():
        st.error(f"Mapping file missing: {MAPPING_XLSX}")
        return

    try:
        xls = pd.ExcelFile(MAPPING_XLSX)
        sheets = xls.sheet_names
        
        active_sheet = st.selectbox("Select Table:", sheets)
        
        if active_sheet:
            _edit_sheet(active_sheet)
            
    except Exception as e:
        st.error(f"Error reading mappings: {e}")

def _edit_sheet(sheet_name):
    # Load specific sheet
    df = pd.read_excel(MAPPING_XLSX, sheet_name=sheet_name, dtype=str)
    
    # Configure Grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(editable=True, resizable=True)
    gb.configure_grid_options(domLayout='normal')
    grid_opts = gb.build()
    
    st.info(f"Editing: **{sheet_name}**")
    
    grid_out = AgGrid(df, gridOptions=grid_opts, height=400, fit_columns_on_grid_load=False)
    
    if st.button("Save Changes"):
        _save_excel_changes(sheet_name, grid_out['data'])

def _save_excel_changes(sheet_name, new_data_dict):
    try:
        new_df = pd.DataFrame(new_data_dict)
        
        # We need to preserve other sheets
        # This is a bit heavy but safe
        xl_file = pd.ExcelFile(MAPPING_XLSX)
        all_sheets = {s: pd.read_excel(MAPPING_XLSX, sheet_name=s, dtype=str) for s in xl_file.sheet_names}
        
        # Update current
        all_sheets[sheet_name] = new_df
        
        with pd.ExcelWriter(MAPPING_XLSX, engine='openpyxl') as writer:
            for s_name, s_df in all_sheets.items():
                s_df.to_excel(writer, sheet_name=s_name, index=False)
        
        st.success("Changes saved successfully!")
    except Exception as e:
        st.error(f"Save failed: {e}")

if __name__ == "__main__":
    init_ui()
