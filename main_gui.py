import streamlit as st
import pandas as pd
import os
from pathlib import Path
from st_aggrid import AgGrid, GridOptionsBuilder

# Backend Import
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

# --- CSS STYLING ---
def load_custom_css():
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; }
        /* Custom Button Styling to match SAP Blue */
        div.stButton > button:first-child {
            background-color: #0072C6;
            color: white;
            border-radius: 4px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: bold;
        }
        div.stButton > button:hover {
            background-color: #005a9e;
            color: white;
            border-color: #005a9e;
        }
        </style>
    """, unsafe_allow_html=True)

def init_ui():
    load_custom_css()
    
    # --- SIDEBAR NAV ---
    with st.sidebar:
        st.title("🏥 SAP Tool")
        
        st.markdown("### Menu")
        page = st.radio("Navigatie", ["🚀 Run Conversie", "🛠️ Bewerk mappings", "ℹ️ Help"], label_visibility="collapsed")
        
        st.divider()
        st.markdown("### 📊 Status Monitor")
        
        # Simple stats
        if INPUT_PATH.exists():
            files = list(INPUT_PATH.glob('*.xlsx')) + list(INPUT_PATH.glob('*.csv'))
            st.metric("📄 Input Bestanden", len(files))
        
        if OUTPUT_PATH.exists():
            out_files = list(OUTPUT_PATH.glob('*.csv'))
            st.metric("📤 Gegenereerde Bestanden", len(out_files))

    # --- MAIN ROUTING ---
    if page == "🚀 Run Conversie":
        render_conversion_view()
    elif page == "🛠️ Bewerk mappings":
        render_mapping_view()
    elif page == "ℹ️ Help":
        render_help_view()

def render_conversion_view():
    st.title("🚀 Data Conversie Uitvoeren")
    st.markdown("Transformeer legacy ziekenhuisdata naar SAP-ready CSV formaten.")
    
    if not INPUT_PATH.exists():
        st.warning(f"Map '{INPUT_PATH}' bestaat niet.")
        return

    files = [f.name for f in INPUT_PATH.iterdir() if f.suffix.lower() in ('.xlsx', '.csv')]
    
    if not files:
        st.info("Geen bestanden gevonden in data/input.")
        return

    # Modern 2-Column Layout
    col_config, col_result = st.columns([1, 2], gap="large")
    
    with col_config:
        with st.container(border=True):
            st.subheader("1. Configuratie")
            selected_file = st.selectbox("📂 Kies Bestand", files)
            preview_rows = st.slider("👁️ Preview regels", 5, 50, 10)
            
            st.markdown("---")
            run_btn = st.button("▶️ Start Conversie", use_container_width=True)
            
            if run_btn:
                st.session_state['active_run'] = True
                st.session_state['selected_file'] = selected_file
                st.session_state['preview_rows'] = preview_rows

    with col_result:
        st.subheader("2. Resultaat & Output")
        
        # Logic to persist the view after button press using session state concepts
        if st.session_state.get('active_run'):
            # Only run if the selected file matches what we clicked "Run" for
            if st.session_state.get('selected_file') == selected_file:
                 _run_transformation_process(selected_file, preview_rows)
            else:
                 st.info("⚠️ Configuratie gewijzigd. Klik opnieuw op Start.")
        else:
            st.info("👈 Selecteer een bestand en klik op Start om te beginnen.")

def _run_transformation_process(filename, n_rows):
    converter = SAPDataConverter(settings_file='settings.json')
    full_path = str(INPUT_PATH / filename)

    with st.spinner('Bezig met analyseren en converteren...'):
        try:
            result_df = converter.run(full_path)
            
            if result_df.empty:
                st.error("⚠️ Conversie leverde geen data op (Check filtering/input).")
            else:
                # Success Logic
                st.success(f"✅ Succes! {len(result_df)} rijen gegenereerd.")
                
                # Tabs for different views of the result
                tab_table, tab_raw = st.tabs(["📄 Tabel Weergave", "📝 Ruwe Data"])
                
                with tab_table:
                    st.dataframe(result_df.head(n_rows), use_container_width=True)
                
                with tab_raw:
                    st.code(result_df.head(5).to_csv(sep=';', index=False), language='csv')
                
                # Download Button
                csv_data = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="💾 Download Volledige CSV",
                    data=csv_data,
                    file_name=f"SAP_Upload_{filename}.csv",
                    mime="text/csv",
                    type="primary"
                )
                
        except Exception as e:
            st.error("❌ Fout tijdens conversie")
            with st.expander("Toon technische fout"):
                st.exception(e)

def render_mapping_view():
    st.title("🛠️ Mapping Editor")
    
    if not MAPPING_XLSX.exists():
        st.error(f"Fout: Bestand niet gevonden: {MAPPING_XLSX}")
        return

    try:
        xls = pd.ExcelFile(MAPPING_XLSX)
        sheets = xls.sheet_names
        
        # Split layout
        col_nav, col_editor = st.columns([1, 4])
        
        with col_nav:
            st.markdown("### Tabellen")
            active_sheet = st.radio("Kies tabel:", sheets, label_visibility="collapsed")
            st.info(f"Je bewerkt nu: **{active_sheet}**")
        
        with col_editor:
            _edit_sheet(active_sheet)
            
    except Exception as e:
        st.error(f"Fout bij laden Excel: {e}")

def _edit_sheet(sheet_name):
    df = pd.read_excel(MAPPING_XLSX, sheet_name=sheet_name, dtype=str)
    
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(editable=True, resizable=True, filter=True)
    gb.configure_grid_options(domLayout='autoHeight')
    grid_opts = gb.build()
    
    grid_out = AgGrid(
        df, 
        gridOptions=grid_opts, 
        height=500, 
        fit_columns_on_grid_load=False,
        theme='material' # Clean theme
    )
    
    if st.button("💾 Wijzigingen Opslaan naar Excel"):
        _save_excel_changes(sheet_name, grid_out['data'])

def _save_excel_changes(sheet_name, new_data_dict):
    try:
        new_df = pd.DataFrame(new_data_dict)
        
        # Load all sheets to preserve them
        xl_file = pd.ExcelFile(MAPPING_XLSX)
        all_sheets = {s: pd.read_excel(MAPPING_XLSX, sheet_name=s, dtype=str) for s in xl_file.sheet_names}
        
        # Update specific sheet
        all_sheets[sheet_name] = new_df
        
        with pd.ExcelWriter(MAPPING_XLSX, engine='openpyxl') as writer:
            for s_name, s_df in all_sheets.items():
                s_df.to_excel(writer, sheet_name=s_name, index=False)
        
        st.toast(f"✅ Tabblad '{sheet_name}' is succesvol opgeslagen!", icon="💾")
    except Exception as e:
        st.error(f"Opslaan mislukt: {e}")

def render_help_view():
    st.title("ℹ️ Informatie")
    st.markdown("""
    #### Over deze applicatie
    Deze tool converteert legacy data naar een aanpasbaar **SAP MATMAS** formaat.
    
    #### Workflow
    1. **Input**: Bestand met tabbladen 'Artikels' en 'Locatie' in `data/input`.
    2. **Conversie**: 
       - Filtert op Actief = 'J'.
       - Controleert Einddatum.
       - Voert mappings uit (zie tabblad mappings).
    3. **Output**: Genereert CSV in `data/output`.
    
    #### Versiebeheer
    - **Backend**: v2.0 (Refactored)
    - **UI**: v2.1 (White Theme & Enhanced Layout)
    """)

if __name__ == "__main__":
    init_ui()
