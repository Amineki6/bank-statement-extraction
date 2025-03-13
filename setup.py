#!/usr/bin/env python3
import os
from typing import List
from pathlib import Path

from log_handling import log_handler
from log_handling.log_handler import Logger, Module

logger: Logger = log_handler.get_instance()

# Directories required for operation
SOURCE_DIR: str = 'source'
TARGET_DIR: str = 'dest'
EXPORT_DIR: str = 'export'
FAILED_DIR: str = 'failed'
IMAGE_DIR: str = 'image'
DB_PATH: str = os.path.join(EXPORT_DIR, 'database.db')

required_dirs: List[str] = [
    SOURCE_DIR,
    TARGET_DIR,
    FAILED_DIR,
    IMAGE_DIR
]

# GPT
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error('OPENAI_API_KEY not set, terminating.', module=Module.SETUP)
    exit(-1)


def create_dirs():
    """
    Creates all directories required for the application.
    :return:
    """
    global required_dirs
    logger.info('Creating directories required for the application.', module=Module.SETUP)
    for required_dir in required_dirs:
        if os.path.isdir(required_dir):
            continue
        try:
            os.makedirs(required_dir)
            logger.info(f'Directory \"{required_dir}\" created.', module=Module.SETUP)
        except Exception as e:
            logger.error('Error creating directory \"{}\". Trace:'.format(required_dir), e, module=Module.SETUP)
            exit(-1)
