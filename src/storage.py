import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        connection = get_connection(self.db_path)
        try:
            df = df.astype(object).where(df.notna(), None)
            sql_statement = "DELETE FROM movies"
            connection.execute(sql_statement)

            sql_statement = "INSERT INTO movies (title, release_year, rating, genre) VALUES (?, ?, ?, ?)"
            rows = df.values.tolist()
            connection.executemany(sql_statement, rows)
            connection.commit()

        except sqlite3.Error:
            logger.info("Save Failed", exc_info=True)
            connection.rollback()
        finally:
            connection.close()
            logger.debug(f"Saved {len(rows)} movies")


    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT title, release_year, rating, genre FROM movies ORDER BY id"
            rows = connection.execute(sql_statement).fetchall()
            return pd.DataFrame(rows, columns=MOVIE_COLUMNS)
        finally:
            connection.close()


    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies ORDER BY id"
            rows = connection.execute(sql_statement).fetchall()
            rows = rows[:limit]
            logger.debug(f"Selected {len(rows)} rows from columns: {selected_columns}")
            return list(dict(row) for row in rows)

        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        try:
            connection = get_connection(self.db_path)
            sql_statement = "SELECT COUNT(*) FROM movies"
            count = connection.execute(sql_statement).fetchone()[0]
            return count
        finally:
            connection.close()


    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies WHERE rating >= {min_rating} ORDER BY rating DESC, id ASC LIMIT {limit}"
            rows = connection.execute(sql_statement).fetchall()
            logger.debug(f"Returned {len(rows)} rows from selected columns: {selected_columns}")
            return list(dict(row) for row in rows)
        finally:
            connection.close()

