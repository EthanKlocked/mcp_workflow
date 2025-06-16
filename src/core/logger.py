import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict

from dotenv import load_dotenv

load_dotenv()

class Logger:
    """
    from .env :
    - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - LOG_FORMAT (simple, json)
    - LOG_DIR
    - LOG_FILE_MAX_BYTES (unit : byte)
    - LOG_FILE_BACKUP_COUNT
    - LOG_TO_CONSOLE (True/False)
    - LOG_TO_FILE (True/False)
    """

    # Dict for checking singletone
    _instances: Dict[str, 'Logger'] = {}

    def __init__(self, name: str = None):
        self.name = name or __name__
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "simple").lower()
        self.log_dir = os.getenv("LOG_DIR", "logs")
        self.log_file_max_bytes = int(os.getenv("LOG_FILE_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
        self.log_file_backup_count = int(os.getenv("LOG_FILE_BACKUP_COUNT", 5))
        self.log_to_console = os.getenv("LOG_TO_CONSOLE", "True").lower() == "true"
        self.log_to_file = os.getenv("LOG_TO_FILE", "True").lower() == "true"        
        self._setup_logging()
        
    def _setup_logging(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        if not self.logger.handlers:
            if self.log_format == "json":
                formatter = logging.Formatter(
                    '{"timestamp":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}'
                )
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
                )            
            # Console Settings
            if self.log_to_console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)            
            # Log File Settings
            if self.log_to_file:
                Path(self.log_dir).mkdir(parents=True, exist_ok=True)                
                # general logs
                log_file = os.path.join(self.log_dir, f"{self.name.replace('.', '_')}.log")
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=self.log_file_max_bytes,
                    backupCount=self.log_file_backup_count
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)                
                # error logs
                error_log_file = os.path.join(self.log_dir, f"{self.name.replace('.', '_')}_error.log")
                error_file_handler = RotatingFileHandler(
                    error_log_file,
                    maxBytes=self.log_file_max_bytes,
                    backupCount=self.log_file_backup_count
                )
                error_file_handler.setFormatter(formatter)
                error_file_handler.setLevel(logging.ERROR)
                self.logger.addHandler(error_file_handler)
    
    def get_logger(self) -> logging.Logger:
        return self.logger
    
    def debug(self, message: str, extra: Optional[dict] = None):
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, extra: Optional[dict] = None):
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, extra: Optional[dict] = None):
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, extra: Optional[dict] = None, exc_info: bool = False):
        self.logger.error(message, extra=extra, exc_info=exc_info)
    
    def critical(self, message: str, extra: Optional[dict] = None, exc_info: bool = True):
        self.logger.critical(message, extra=extra, exc_info=exc_info)
    
    def exception(self, message: str, extra: Optional[dict] = None):
        self.logger.exception(message, extra=extra)


############################################################    
####### Singletone Wrapper #################################
############################################################
def get_logger(name: str = None) -> Logger:
    name = name or __name__    
    if name not in Logger._instances:
        Logger._instances[name] = Logger(name)        
    return Logger._instances[name]