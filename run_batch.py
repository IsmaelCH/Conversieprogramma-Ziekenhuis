import argparse
import logging
from pathlib import Path
from datetime import datetime
from backend.processing import SAPDataConverter

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchExecutor:
    def __init__(self, input_dir: str, output_dir: str, ref_date: str = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.ref_date = ref_date or datetime.now().strftime('%Y-%m-%d')
        self.converter = SAPDataConverter(settings_file='settings.json') # Uses updated settings file

    def run(self):
        self.output_dir.mkdir(exist_ok=True, parents=True)
        log_records = []

        files = list(self.input_dir.glob('*_ZH*.xlsx'))
        
        if not files:
            logger.warning(f"No matching files (*_ZH*.xlsx) found in {self.input_dir}")
            return

        for file_path in files:
            try:
                logger.info(f"Processing: {file_path.name}")
                result_df = self.converter.run(str(file_path), self.ref_date)
                
                # Timestamp for filename
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                out_name = f"{file_path.stem}_SAP_{ts}.csv"
                out_path = self.output_dir / out_name
                
                result_df.to_csv(out_path, sep=';', index=False, encoding='utf-8-sig')
                
                msg = f"{file_path.name}: SUCCESS -> {out_name}"
                log_records.append(msg)
                logger.info(msg)
                
            except Exception as e:
                msg = f"{file_path.name}: ERROR -> {e}"
                log_records.append(msg)
                logger.error(msg)

        self._write_summary_log(log_records)

    def _write_summary_log(self, records):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.output_dir / f'batch_summary_{timestamp}.txt'
        
        with open(log_file, 'w', encoding='utf-8') as f:
            for line in records:
                f.write(line + '\n')
        
        logger.info(f"Batch processing finished. Summary: {log_file}")

def cli_entry_point():
    parser = argparse.ArgumentParser(description="Automated SAP Data Migration Batch Tool")
    parser.add_argument('--input', required=True, help='Directory containing source files')
    parser.add_argument('--output', required=True, help='Directory for generated files')
    parser.add_argument('--date', required=False, help='Reference Date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    executor = BatchExecutor(args.input, args.output, args.date)
    executor.run()

if __name__ == "__main__":
    cli_entry_point()
