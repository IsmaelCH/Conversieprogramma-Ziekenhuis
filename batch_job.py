import argparse
import os
import glob
import pandas as pd
from datetime import datetime
from src.etl_logic import run_conversion

def main():
    parser = argparse.ArgumentParser(description="SAP Data Migratie Batch Job")
    parser.add_argument('--input', required=True, help='Input map met bronbestanden')
    parser.add_argument('--output', required=True, help='Output map voor resultaten')
    parser.add_argument('--date', required=False, help='Peildatum (YYYY-MM-DD), default = vandaag')
    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output
    peildatum = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
    os.makedirs(output_dir, exist_ok=True)
    log_lines = []

    pattern = os.path.join(input_dir, '*_ZH*.xlsx')
    files = glob.glob(pattern)
    if not files:
        print(f"Geen bestanden gevonden in {input_dir} met patroon *_ZH*.xlsx")
        return

    for file in files:
        try:
            print(f"Start conversie: {file}")
            df = run_conversion(file, peildatum)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            base = os.path.splitext(os.path.basename(file))[0]
            out_file = os.path.join(output_dir, f"{base}_SAP_{ts}.csv")
            df.to_csv(out_file, sep=';', index=False, encoding='utf-8-sig')
            log_lines.append(f"{file}: SUCCES -> {out_file}")
        except Exception as e:
            log_lines.append(f"{file}: FOUT -> {e}")
            print(f"Fout bij verwerken van {file}: {e}")

    # Schrijf logbestand weg
    log_path = os.path.join(output_dir, f'batch_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt')
    with open(log_path, 'w', encoding='utf-8') as f:
        for line in log_lines:
            f.write(line + '\n')
    print(f"Batchverwerking klaar. Logbestand: {log_path}")

if __name__ == "__main__":
    main()
