#!/usr/bin/env python3
import glob
import json
import os
import sqlite3
from sqlite3 import Connection, Cursor
from typing import List, Dict

import setup
from log_handling import log_handler
from log_handling.log_handler import Logger, Module

logger: Logger = log_handler.get_instance()


class Database:
    """
    Handles the sqlite db connection.
    """
    DATABASE_PATH: str = os.path.join(setup.DB_PATH)
    MIGRATIONS_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')
    INSERT_DOCUMENT_QUERY: str = 'INSERT INTO DOCUMENTS VALUES (NULL, ?, ?)'
    EXPORT_ALL_DOCUMENTS_QUERY: str = 'SELECT DOCUMENT_NAME, DOCUMENT_DATA FROM DOCUMENTS'

    def _connect(self) -> Connection:
        """
        Connect to the sqlite3 database.
        :return: the sqlite3 db connection.
        """
        logger.info(f'Connecting to database \"{self.DATABASE_PATH}\"...', module=Module.DB)
        return sqlite3.connect(self.DATABASE_PATH)

    def _apply_migrations(self) -> None:
        """
        Applies the database migrations and sets up the db tables.
        :return:
        """
        globs: List[str] = glob.glob(os.path.join(self.MIGRATIONS_PATH, '*.sql'))
        logger.info(f'Applying {len(globs)} migrations...', module=Module.DB)
        for file in globs:
            with open(file, 'r') as f:
                sql: str = f.read()
                logger.debug(f'Applying migration:\n\n{sql}\n', module=Module.DB)
                self.conn.execute(sql)
                self.conn.commit()
        logger.info('Finished applying migrations.', module=Module.DB)

    def export_data(self) -> List[Dict[str, any]]:
        """
        Export all data from the database.
        :return:
        """
        cursor: Cursor = self.conn.cursor()
        rows: List[any] = cursor.execute(self.EXPORT_ALL_DOCUMENTS_QUERY).fetchall()
        return [
            {
                'document_name': data[0],
                'document_data': json.loads(data[1])
            } for data in rows
        ]

    def import_pdf_data(self, pdf_metadata_dictionary: Dict[str, any]) -> None:
        """
        Imports extracted data from pdf files to the database.
        :param pdf_metadata_dictionary: pdf data dictionary, containing extracted ocr data from gpt.
        :return:
        """
        document_name: str = os.path.basename(pdf_metadata_dictionary['pdf_path'])
        json_data: str = json.dumps(pdf_metadata_dictionary)
        self.conn.execute(self.INSERT_DOCUMENT_QUERY, [document_name, json_data])
        self.conn.commit()
        logger.info('Data for document {} written to db.'.format(document_name), module=Module.DB)

    def __init__(self, db_path: str = DATABASE_PATH):
        """
        Default constructor.
        :param db_path: Path to the database, default: persistence/database.db.
        :return:
        """
        logger.info('Initializing DB handler...', module=Module.DB)
        self.DATABASE_PATH = db_path
        try:
            self.conn: Connection = self._connect()
            self._apply_migrations()
            logger.info('DB Handler initialized.', module=Module.DB)
        except Exception as e:
            logger.error('Failed to initialize DB handler. Trace:', e, module=Module.DB)
            exit(-1)


# DB Handler singleton
database: Database = Database()


# Test only
if __name__ == '__main__':
    database.export_data()