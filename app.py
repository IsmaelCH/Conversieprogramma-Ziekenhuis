import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder
# Zorg dat deze import werkt. Als je map structuur anders is, pas dit aan.
try:
    from src.etl_logic import run_conversion
except ImportError:
    st.error("Fout: Kan 'src.etl_logic' niet vinden. Controleer je mappenstructuur.")
    st.stop()

# 1. Page Config MOET als eerste
st.set_page_config(page_title="SAP Migratie Tool", layout="wide")

st.title("🏥 ERP Migratie Tool: Legacy naar SAP")

# Configuratie paden (Pas aan indien nodig)
INPUT_DIR = "data/input"
OUTPUT_DIR = "data/output"
MAPPING_FILE = os.path.join("data", "mappings", "Opdracht_mappingtabellen_ZH01.xlsx")

# Zorg dat output dir bestaat
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Tabs
tab1, tab2 = st.tabs(["🚀 Conversie Uitvoeren", "🛠️ Mapping Editor"])

# --- TAB 1: CONVERSIE ---
with tab1:
    st.header("Start dataconversie")
    
    if not os.path.exists(INPUT_DIR):
        st.warning(f"Map '{INPUT_DIR}' bestaat niet. Maak deze aan en plaats je bestanden.")
    else:
        files = [f for f in os.listdir(INPUT_DIR) if f.endswith(('.xlsx', '.csv'))]
        
        if not files:
            st.info("Geen Excel of CSV bestanden gevonden in data/input.")
        else:
            selected_file = st.selectbox("Kies bronbestand:", files)
            
            # Aantal rijen instelbaar
            n_rows = st.number_input("Aantal rijen tonen in preview:", min_value=1, max_value=1000, value=10, step=1)
            
            if st.button("Start Conversie"):
                with st.spinner('Bezig met converteren...'):
                    try:
                        full_path = os.path.join(INPUT_DIR, selected_file)
                        
                        # Voer conversie uit
                        result_df = run_conversion(full_path)
                        
                        if result_df.empty:
                            st.error("Conversie leverde geen resultaten op. Controleer de logs.")
                        else:
                            st.success(f"Conversie geslaagd! {len(result_df)} rijen gegenereerd.")
                            
                            # Preview
                            st.dataframe(result_df.head(n_rows))
                            
                            # Download
                            csv = result_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "💾 Download SAP Import Bestand",
                                csv,
                                "Oplaadgegevens_SAP.csv",
                                "text/csv"
                            )
                            
                    except Exception as e:
                        st.error(f"Er ging iets mis tijdens de conversie: {e}")
                        # Toon de volledige foutmelding in een uitklapmenu voor debugging
                        with st.expander("Zie technische details"):
                            st.exception(e)

# --- TAB 2: MAPPING EDITOR ---
with tab2:
    st.header("Bewerk Mapping Tabellen (Excel)")
    
    if not os.path.exists(MAPPING_FILE):
        st.error(f"Mapping bestand niet gevonden: {MAPPING_FILE}")
        st.info("Zorg dat 'Opdracht_mappingtabellen_ZH01.xlsx' in de map 'data/mappings' staat.")
    else:
        try:
            # Lees tabbladen
            xl = pd.ExcelFile(MAPPING_FILE)
            sheet_names = xl.sheet_names
            
            selected_sheet = st.selectbox("Kies mapping (Tabblad):", sheet_names)
            
            if selected_sheet:
                # Lees de specifieke sheet
                # dtype=str zorgt dat '010' niet verandert in 10
                df_map = pd.read_excel(MAPPING_FILE, sheet_name=selected_sheet, dtype=str)
                
                # Editor configureren
                gb = GridOptionsBuilder.from_dataframe(df_map)
                gb.configure_default_column(editable=True, resizable=True)
                gb.configure_grid_options(domLayout='normal')
                gridOptions = gb.build()
                
                st.info(f"Je bewerkt nu tabblad: **{selected_sheet}**")
                
                # De Grid
                grid_response = AgGrid(
                    df_map, 
                    gridOptions=gridOptions, 
                    height=400,
                    fit_columns_on_grid_load=False # Zet op False als kolommen te smal worden
                )
                
                if st.button("Wijzigingen Opslaan naar Excel"):
                    try:
                        updated_data = pd.DataFrame(grid_response['data'])
                        
                        # We moeten voorzichtig zijn om niet de andere sheets te wissen!
                        # 1. Lees alle sheets in het geheugen
                        all_sheets = {}
                        for sheet in sheet_names:
                            if sheet == selected_sheet:
                                all_sheets[sheet] = updated_data
                            else:
                                all_sheets[sheet] = pd.read_excel(MAPPING_FILE, sheet_name=sheet, dtype=str)
                        
                        # 2. Schrijf alles terug naar het bestand
                        with pd.ExcelWriter(MAPPING_FILE, engine='openpyxl') as writer:
                            for sheet_name, data in all_sheets.items():
                                data.to_excel(writer, sheet_name=sheet_name, index=False)
                                
                        st.success(f"Tabblad '{selected_sheet}' succesvol opgeslagen!")
                        
                    except Exception as e:
                        st.error(f"Fout bij opslaan: {e}")
                        
        except Exception as e:
            st.error(f"Kan Excel bestand niet lezen: {e}")