import os
import mysql.connector

from backend.database.schema_mapper import SchemaMapper


class CatalogDatabase:
    """
    Generic MySQL database provider.

    Responsibilities:
    1. Create MySQL connections.
    2. Execute generic SELECT queries.
    3. Execute parameterized queries.
    4. Keep database-specific table/column information
       inside SchemaMapper.

    This class does NOT contain:
    - AI logic
    - Conversation logic
    - Entity resolution
    - Product-specific methods
    - Hard-coded column lists
    """

    def __init__(
        self,
        host=None,
        user=None,
        password=None,
        database=None
    ):
        self.config = {
            "host": host or os.getenv(
                "CATALOG_DB_HOST",
                "localhost"
            ),
            "user": user or os.getenv(
                "CATALOG_DB_USER",
                "root"
            ),
            "password": password or os.getenv(
                "CATALOG_DB_PASSWORD",
                ""
            ),
            "database": database or os.getenv(
                "CATALOG_DB_NAME",
                "ai_catalog"
            ),
            "port": int(os.getenv(
                "CATALOG_DB_PORT",
                "3306"
            ))
        }

    # =========================================================
    # CONNECTION
    # =========================================================

    def _get_connection(self):
        """
        Create and return a MySQL database connection.
        """

        return mysql.connector.connect(
            **self.config
        )

    # =========================================================
    # EXECUTE SELECT
    # =========================================================

    def execute_select(
        self,
        query,
        params=None,
        dictionary=True
    ):
        """
        Execute a SELECT query and return all rows.

        Parameters
        ----------
        query : str
            SQL SELECT query.

        params : tuple/list, optional
            Parameterized query values.

        dictionary : bool
            Return rows as dictionaries when True.
        """

        connection = self._get_connection()
        cursor = None

        try:

            cursor = connection.cursor(
                dictionary=dictionary
            )

            cursor.execute(
                query,
                params or ()
            )

            return cursor.fetchall()

        finally:

            if cursor is not None:
                cursor.close()

            connection.close()

    # =========================================================
    # EXECUTE SINGLE SELECT
    # =========================================================

    def execute_one(
        self,
        query,
        params=None,
        dictionary=True
    ):
        """
        Execute a SELECT query and return one row.
        """

        connection = self._get_connection()
        cursor = None

        try:

            cursor = connection.cursor(
                dictionary=dictionary
            )

            cursor.execute(
                query,
                params or ()
            )

            return cursor.fetchone()

        finally:

            if cursor is not None:
                cursor.close()

            connection.close()

    # =========================================================
    # GET ALL RECORDS
    # =========================================================

    def get_all_records(self):
        """
        Retrieve all records from the table defined
        by SchemaMapper.

        No column names are hard-coded here.
        """

        table_name = (
            SchemaMapper.get_table_name()
        )

        query = (
            f"SELECT * "
            f"FROM `{table_name}`"
        )

        return self.execute_select(
            query
        )

    # =========================================================
    # COUNT RECORDS
    # =========================================================

    def count_records(self):
        """
        Return total number of records.
        """

        table_name = (
            SchemaMapper.get_table_name()
        )

        query = (
            f"SELECT COUNT(*) AS total "
            f"FROM `{table_name}`"
        )

        result = self.execute_one(
            query
        )

        if not result:
            return 0

        return result.get(
            "total",
            0
        )

    # =========================================================
    # GET DISTINCT VALUES
    # =========================================================

    def get_distinct_values(
        self,
        database_field,
        filters=None
    ):
        """
        Get distinct values for a database column.

        Parameters
        ----------
        database_field : str
            Actual database column name.

        filters : dict
            Database column → value mapping.
        """

        if not database_field:
            return []

        table_name = (
            SchemaMapper.get_table_name()
        )

        query = (
            f"SELECT DISTINCT "
            f"`{database_field}` "
            f"FROM `{table_name}`"
        )

        filters = filters or {}

        conditions = []
        values = []

        for field, value in filters.items():

            if value is None:
                continue

            if isinstance(value, str):
                if not value.strip():
                    continue

            conditions.append(
                f"`{field}` = %s"
            )

            values.append(value)

        if conditions:

            query += (
                " WHERE "
                + " AND ".join(conditions)
            )

        query += (
            f" ORDER BY `{database_field}`"
        )

        rows = self.execute_select(
            query,
            tuple(values),
            dictionary=False
        )

        return [
            row[0]
            for row in rows
            if row[0] is not None
        ]

    # =========================================================
    # SEARCH
    # =========================================================

    def search(
        self,
        database_filters=None
    ):
        """
        Generic database search.

        database_filters must contain actual database
        column names.

        Example:

            {
                "OEMName": "BMW",
                "Year": 2023
            }
        """

        table_name = (
            SchemaMapper.get_table_name()
        )

        database_filters = (
            database_filters or {}
        )

        query = (
            f"SELECT * "
            f"FROM `{table_name}`"
        )

        conditions = []
        values = []

        for field, value in database_filters.items():

            if value is None:
                continue

            if isinstance(value, str):
                if not value.strip():
                    continue

            conditions.append(
                f"`{field}` = %s"
            )

            values.append(value)

        if conditions:

            query += (
                " WHERE "
                + " AND ".join(conditions)
            )

        return self.execute_select(
            query,
            tuple(values)
        )

    # =========================================================
    # GET BY ID
    # =========================================================

    def get_by_id(self, record_id):
        """
        Retrieve one record using the database ID column
        defined by SchemaMapper.
        """

        database_field = (
            SchemaMapper.get_database_field(
                "id"
            )
        )

        if database_field is None:
            return None

        table_name = (
            SchemaMapper.get_table_name()
        )

        query = (
            f"SELECT * "
            f"FROM `{table_name}` "
            f"WHERE `{database_field}` = %s "
            f"LIMIT 1"
        )

        return self.execute_one(
            query,
            (record_id,)
        )

    # =========================================================
    # TEST CONNECTION
    # =========================================================

    def test_connection(self):
        """
        Check whether the database connection works.
        """

        connection = None

        try:

            connection = self._get_connection()

            return True

        except mysql.connector.Error:

            return False

        finally:

            if connection is not None:
                connection.close()