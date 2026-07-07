import os
import sys
import json
import click
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
from app.utils.logging_config import setup_logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging(log_level)

from app.clients.sarvam_client import SarvamClient
from app.services.extraction_service import ExtractionService

@click.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to the electricity bill file (PDF/Image).")
@click.option("--lang", "-l", default=None, help="BCP-47 language code of the bill (e.g. en-IN, hi-IN, gu-IN). If omitted, language is auto-detected.")
@click.option("--output", "-o", type=click.Path(), help="Path to save the extracted JSON output.")
def main(file: str, lang: str, output: str):
    """CLI to extract structured, normalized JSON data from a single electricity bill using Sarvam AI."""
    logger.info(f"CLI: Starting single file extraction on: {file} (language: {lang or 'auto-detect'})")
    
    try:
        # Initialize client and service
        client = SarvamClient()
        service = ExtractionService(client)
        
        # Run sync digitization and extraction pipeline
        result = service.digitize_and_extract_sync(file, language=lang)
        
        # Serialize model output
        result_dict = result.model_dump()
        
        # Determine output save path
        save_path = output
        if not save_path:
            os.makedirs("outputs", exist_ok=True)
            doc_name = os.path.splitext(os.path.basename(file))[0]
            save_path = os.path.join("outputs", f"{doc_name}.json")
            
        # Save JSON output with graceful error handling
        try:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)) or ".", exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON successfully saved to {save_path}")
        except Exception as e:
            logger.exception(f"Error saving JSON to {save_path}: {e}")
            
        # Print JSON output to console
        click.echo(json.dumps(result_dict, indent=2, ensure_ascii=False))
        
        # Print the saved location
        click.echo("Saved result:")
        click.echo(save_path)
            
    except Exception as e:
        logger.error(f"CLI: Extraction failed: {e}", exc_info=True)
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
