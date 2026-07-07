import os
import logging
import sys

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures centralized logging for the benchmark application."""
    logger = logging.getLogger("sarvam_bill_benchmark")
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Suppress third-party warnings and noisy pypdf logs
    import warnings
    warnings.filterwarnings("ignore")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    
    # Ensure logs folder exists and add a rotating file logger
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(logs_dir, "benchmark.log"), encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    logger.addHandler(file_handler)
    
    logger.propagate = False
    return logger

# Get default logger instance
logger = logging.getLogger("sarvam_bill_benchmark")
