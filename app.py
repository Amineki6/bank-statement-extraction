#!/usr/bin/env python3
import glob
import os
from typing import List, Dict

import setup
import pdf_processor
import persistence.db_handler
from csv_handling import csv_handler
from csv_handling.csv_handler import CSVHandler
from log_handling import log_handler
from log_handling.log_handler import Logger, Module
from persistence.db_handler import Database

logger: Logger = log_handler.get_instance()
database: Database = persistence.db_handler.database
csv_handler: CSVHandler = csv_handler.csv_handler


def enumerate_files() -> List[str]:
    """
    Enumerates the files within the import directory and returns a list of pdf files.
    :return: list of all pdf files in the import directory.
    """
    files: List[str] = glob.glob(f'{setup.SOURCE_DIR}/*.pdf')
    logger.info(f'Found {len(files)} pdf files.', module=Module.MAIN)
    return files


def _get_csv_headers() -> List[str]:
    """
    (For now) Hardcoded list of csv headers for the transaction csv file.
    :return: the csv headers as a list.
    """
    return [
        'Transaction Date',
        'Transaction Amount',
        'Transaction Text'
    ]


def _get_transaction_list(page: Dict[str, any]) -> List[List[str]]:
    """
    Gets the transaction data from the document page and format it for csv export.
    :param page: the pdf document page.
    :return: a list of csv data rows.
    """
    transactions: List[List[str]] = []
    for transaction in (page['transactions']).get('transactions', []):
        transaction_date: str = transaction.get('date', '')
        transaction_amount: str = transaction.get('amount', '')
        transaction_text: str = transaction.get('transaction_text', '')
        if not transaction_amount or not transaction_date:
            logger.error(f'Error reading transaction data on page {page["text"]}, '
                         'date or amount was missing.', module=Module.MAIN)
            continue
        transactions.append([transaction_date, transaction_amount, transaction_text])
    return transactions


def _export_document(
        filepath: str,
        document_data: Dict[str, any]
) -> None:
    """
    Creates a csv export for each processed pdf document.
    :param filepath: path for the csv output file.
    :param document_data: the extracted data.
    :return:
    """
    transactions: List[List[str]] = []
    for page in document_data['page_content']:
        if 'transactions' not in page:
            continue
        transactions.extend(_get_transaction_list(page=page))
    headers: List[str] = _get_csv_headers()
    csv_handler.export(
        headers=headers,
        rows=transactions,
        filepath=filepath
    )


def export_transactions() -> None:
    """
    Exports the transactions as a csv file.
    :return:
    """
    documents: List[Dict[str, any]] = database.export_data()
    for document in documents:
        document_name: str = document['document_name']
        csv_document_name: str = document_name.lower().replace('.pdf', '.csv')
        document_data: Dict[str, any] = document['document_data']
        logger.info('Exporting transactions for pdf file', document_name, module=Module.MAIN)
        try:
            filepath: str = os.path.join(setup.EXPORT_DIR, csv_document_name)
            _export_document(filepath, document_data)
            logger.info('CSV file exported to ', csv_document_name, module=Module.MAIN)
        except Exception as e:
            logger.error(f'Error exporting transactions for file {document_name}. Trace:', e, module=Module.MAIN)


def _exec():
    """
    Default standalone exec.
    :return:
    """
    files: List[str] = enumerate_files()
    pdf_processor.process_files(files=files)
    export_transactions()


if __name__ == '__main__':
    logger.info('Starting application...', module=Module.MAIN)
    setup.create_dirs()
    _exec()
