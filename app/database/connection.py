import psycopg

from app.database import config


class Database:

    def __init__(self):

        self.conn = psycopg.connect(

            host=config.DB_HOST,

            port=config.DB_PORT,

            dbname=config.DB_NAME,

            user=config.DB_USER,

            password=config.DB_PASSWORD,

            sslmode=config.DB_SSLMODE

        )

    def cursor(self):

        return self.conn.cursor()

    def commit(self):

        self.conn.commit()

    def rollback(self):

        self.conn.rollback()

    def close(self):

        self.conn.close()