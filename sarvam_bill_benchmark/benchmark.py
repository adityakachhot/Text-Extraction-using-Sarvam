import os
import sys
import json
import time
import click
from dotenv import load_dotenv
from app.clients.sarvam_client import SarvamClient
from app.services.extraction_service import ExtractionService
from app.utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging(log_level)

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}

@click.command()
@click.option("--bills-dir", "-b", default="bills", type=click.Path(exists=True), help="Directory containing the bills.")
@click.option("--output-dir", "-o", default="outputs", type=click.Path(), help="Directory to save output results.")
@click.option("--limit", "-l", default=None, type=int, help="Limit the number of documents to process.")
@click.option("--force", "-f", is_flag=True, default=False, help="Overwrite already processed files.")
def main(bills_dir: str, output_dir: str, limit: int, force: bool):
    """Benchmark runner to scan bills/ folder and process all supported files."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Scan bills directory
    if not os.path.exists(bills_dir):
        click.echo(f"Bills directory '{bills_dir}' not found.", err=True)
        sys.exit(1)
        
    all_files = os.listdir(bills_dir)
    files_to_process = sorted([
        f for f in all_files 
        if os.path.isfile(os.path.join(bills_dir, f)) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
    ])
    
    # Skip already processed files unless force is True
    if not force:
        files_to_process = [
            f for f in files_to_process
            if not os.path.exists(os.path.join(output_dir, f"{os.path.splitext(f)[0]}.json"))
        ]
        
    if limit is not None:
        files_to_process = files_to_process[:limit]
    
    total_documents = len(files_to_process)
    if total_documents == 0:
        click.echo("No supported documents found to process.")
        # Create empty summary and empty failures
        summary = {
            "total_documents": 0,
            "successful": 0,
            "failed": 0,
            "languages_detected": {}
        }
        with open(os.path.join(output_dir, "benchmark_summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        with open(os.path.join(output_dir, "failed_files.json"), "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return

    # Initialize service
    try:
        client = SarvamClient()
        service = ExtractionService(client)
    except Exception as e:
        click.echo(f"Error initializing client/service: {e}", err=True)
        sys.exit(1)
        
    successful = 0
    failed = 0
    languages_detected = {}
    failed_files = {}
    
    for idx, filename in enumerate(files_to_process, 1):
        click.echo(filename)
        filepath = os.path.join(bills_dir, filename)
        
        try:
            # Call extraction service synchronously (allowing dynamic language detection)
            result = service.digitize_and_extract_sync(filepath)
            
            # Save individual JSON result
            base_name = os.path.splitext(filename)[0]
            out_path = os.path.join(output_dir, f"{base_name}.json")
            
            with open(out_path, "w", encoding="utf-8") as f_out:
                json.dump(result.model_dump(), f_out, indent=2, ensure_ascii=False)
                
            successful += 1
            
            # Aggregate language counts
            lang = result.detected_language
            if lang:
                languages_detected[lang] = languages_detected.get(lang, 0) + 1
                
        except Exception as e:
            logger.exception(f"Failed to process '{filename}': {e}")
            failed += 1
            failed_files[filename] = str(e)

        # Small inter-file pause to stay within API rate limits
        if idx < total_documents:
            time.sleep(5)
            
    # Write outputs/benchmark_summary.json
    summary = {
        "total_documents": total_documents,
        "successful": successful,
        "failed": failed,
        "languages_detected": languages_detected
    }
    summary_path = os.path.join(output_dir, "benchmark_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f_sum:
        json.dump(summary, f_sum, indent=2, ensure_ascii=False)
        
    # Write outputs/failed_files.json
    failed_path = os.path.join(output_dir, "failed_files.json")
    with open(failed_path, "w", encoding="utf-8") as f_fail:
        json.dump(failed_files, f_fail, indent=2, ensure_ascii=False)
        
    click.echo("\nBenchmark Completed!")
    click.echo(f"Total processed: {total_documents}")
    click.echo(f"Successful: {successful}")
    click.echo(f"Failed: {failed}")
    click.echo(f"Summary written to: {summary_path}")
    click.echo(f"Failures written to: {failed_path}")

if __name__ == "__main__":
    main()
