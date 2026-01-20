import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder
from src.etl_logic import run_conversion

st.set_page_config(page_title="SAP Migratie Tool", layout="wide")

st.title("🏥 ERP Migratie Tool: Legacy naar SAP")

# Tabs voor navigatie
tab1, tab2 = st.tabs(["🚀 Conversie Uitvoeren", "🛠️ Mapping Tabellen Beheer"])

# --- TAB 1: CONVERSIE ---
with tab1:
    st.header("Start dataconversie")
    
    # 1. Selecteer bronbestand
    input_dir = "data/input"
    files = [f for f in os.listdir(input_dir) if f.endswith('.xlsx') or f.endswith('.csv')]
    selected_file = st.selectbox("Kies bronbestand (ZHxx):", files)
    
    if st.button("Start Conversie"):
        with st.spinner('Bezig met converteren...'):
            try:
                # Roep de logic engine aan
                full_path = os.path.join(input_dir, selected_file)
                result_df = run_conversion(full_path)
                
                st.success("Conversie geslaagd!")
                
                # Toon voorbeeld
                st.dataframe(result_df.head(10))
                
                # Download knop
                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "💾 Download SAP Import Bestand",
                    csv,
                    "Oplaadgegevens_SAP.csv",
                    "text/csv"
                )
            except Exception as e:
                st.error(f"Er ging iets mis: {e}")

# --- TAB 2: MAPPING EDITOR ---
with tab2:
    st.header("Bewerk Mapping Tabellen")
    
    map_dir = "data/mappings"
    map_files = [f for f in os.listdir(map_dir) if f.endswith('.csv')]
    selected_map = st.selectbox("Kies mapping tabel:", map_files)
    
    if selected_map:
        file_path = os.path.join(map_dir, selected_map)
        df_map = pd.read_csv(file_path)
        
        # AG Grid instellingen (Excel-achtige editor)
        gb = GridOptionsBuilder.from_dataframe(df_map)
        gb.configure_default_column(editable=True) # Maak alles bewerkbaar
        gridOptions = gb.build()
        
        st.info("💡 Je kunt direct in de cellen typen.")
        grid_response = AgGrid(
            df_map,
            gridOptions=gridOptions,
            fit_columns_on_grid_load=True,
            height=400
        )
        
        # Opslaan knop
        if st.button("Wijzigingen Opslaan"):
            # Haal de data uit de grid
            updated_df = grid_response['data']
            updated_df = pd.DataFrame(updated_df)
            
            # Overschrijf de CSV
            updated_df.to_csv(file_path, index=False)
            st.success(f"{selected_map} is bijgewerkt!")