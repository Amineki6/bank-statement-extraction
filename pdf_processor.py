import glob
import json
import os.path
import shutil
import subprocess

import persistence.db_handler
from csv import excel_tab
from typing import Dict, List

import pdf2image
from PIL.Image import Image

import ai.prompts
import setup
from ai import azure_openai_connector
from ai.azure_openai_connector import AzureOpenAIAdapter
from log_handling import log_handler
from log_handling.log_handler import Logger, Module

logger: Logger = log_handler.get_instance()
azure_openai_adapter: AzureOpenAIAdapter = azure_openai_connector.azure_open_ai_adapter
database: persistence.db_handler.Database = persistence.db_handler.database


def _create_workdir(filepath: str) -> str:
    """
    Creates a new working directory for the given pdf file.
    :param filepath: path to the pdf file.
    :return: The current working directory.
    :raise Exception: if the working directory already exists.
    """
    sub_dir: str = os.path.basename(filepath).lower().replace('.pdf', '')
    work_dir: str = os.path.join(setup.IMAGE_DIR, sub_dir)
    if os.path.exists(work_dir):
        raise Exception(f'Directory "{work_dir}" already exists - pdf was already processed.')
    os.makedirs(work_dir)
    return work_dir


def _save_images(images: List[Image], workdir: str) -> List[str]:
    """
    Saves the image extracted from pdf2image to the working directory.
    :param images: the images to save.
    :param workdir: the working directory.
    :return: a list of image paths for the saved images.
    """
    for i, img in enumerate(images):
        base_name: str = f'page_{i}.png'
        output_path: str = os.path.join(workdir, base_name)
        img.save(output_path, format='PNG')
    return glob.glob(os.path.join(workdir, '*.png'))


def _split_pages(filepath: str, workdir: str) -> List[str]:
    """
    Splits the given pdf file into separate pages and a PNG image for each.
    :param filepath: path to the pdf file.
    :param workdir: path to the working directory where the PNG images will be created.
    :return: A list of paths to the PNG images.
    """
    images: List[Image] = pdf2image.convert_from_path(filepath, output_folder=workdir)
    logger.debug('Split PDF {} into {} images.'.format(filepath, len(images)), module=Module.PDF)
    return _save_images(images, workdir)


def _ocr_transactions(pdf_page_path: str) -> str:
    """
    Performs OCR on a given pdf page.
    :param pdf_page_path: path to the the image of the page extracted from the PDF.
    :return: the content on the given page.
    """
    transactions_prompt: str = ai.prompts.get_transactions_prompt()
    logger.debug('Performing transactions request with page path', pdf_page_path, module=Module.PDF)
    gpt_response: str = azure_openai_adapter.ask_openai(transactions_prompt, image_uri=pdf_page_path)
    logger.debug('Received response:', gpt_response, module=Module.PDF)
    return gpt_response


def _ocr_account_info(cover_page_path: str) -> str:
    """
    Extracts the customer's account info from the cover page of the transactions report.
    :param cover_page_path: path to the cover page of the transactions report.
    :return: the customer's account info.
    """
    account_info_prompt: str = ai.prompts.get_basic_account_info_prompt()
    logger.debug('Performing account info request with page path', cover_page_path, module=Module.PDF)
    gpt_response: str = azure_openai_adapter.ask_openai(account_info_prompt, image_uri=cover_page_path)
    logger.debug('Received response:', gpt_response, module=Module.PDF)
    return gpt_response


def _create_pdf_metadata(filepath: str, images: List[str]) -> Dict[str, any]:
    """
    For the given pdf, create a metadata dictionary containing the text from each page.
    :param filepath: path to the pdf file.
    :param images: list of image paths for the extracted pdf pages.
    :return: the metadata dictionary.
    """
    cover_page: str = images[0]
    metadata: Dict[str, str] = {
        'pdf_path': filepath,
        'page_count': len(images),
        'page_content': [
            {
                'page_path': page_path,
                'transactions': json.loads(_ocr_transactions(pdf_page_path=page_path))
            }
            for page_path in images
        ],
        'account_information': json.loads(_ocr_account_info(cover_page_path=cover_page))
    }
    return metadata


def _cleanup(file_path: str, workdir: str, success: bool = True) -> None:
    """
    Cleans up the workdir after processing a pdf file.
    :param file_path: file path to the pdf file.
    :param workdir: the working directory for the pdf file.
    :param success: whether or not the pdf was processed successfully.
    :return:
    """
    target_dir: str = setup.TARGET_DIR if success else setup.FAILED_DIR
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    shutil.move(file_path, target_dir)
    logger.info(f'Moved PDF file {file_path} into {target_dir}', module=Module.PDF)


def _process_pdf(filepath: str) -> None:
    """
    Processes a PDF file - extracts pdf pages as images and performs ocr for each page.
    :param filepath: path to the PDF file.
    :return:
    """
    try:
        workdir: str = _create_workdir(filepath=filepath)
    except Exception as e:
        logger.error('Failed to create working directory. Trace:', e, module=Module.PDF)
        return
    success: bool = True
    try:
        images: List[str] = _split_pages(filepath=filepath, workdir=workdir)
        if not len(images):
            raise Exception(f'No images found in "{filepath}".')
        metadata_dictionary: Dict[str, any] = _create_pdf_metadata(filepath=filepath, images=images)
        logger.debug('Processed data:', metadata_dictionary, module=Module.PDF)
        logger.info('Saving OCR data to database', module=Module.PDF)
        database.import_pdf_data(pdf_metadata_dictionary=metadata_dictionary)
    except Exception as e:
        logger.error('An error occurred while processing the PDF. Trace:', e, module=Module.PDF)
        success = False
    finally:
        _cleanup(file_path=filepath, workdir=workdir, success=success)


def process_files(files: List[str]) -> None:
    """
    Processes the given pdf files, extracts data and saves it to the database.
    :param files: the pdf files to process.
    :return:
    """
    for pdf_file in files:
        logger.info('Processing PDF:', pdf_file, module=Module.PDF)
        _process_pdf(pdf_file)
