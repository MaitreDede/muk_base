###################################################################################
#
#    Copyright (c) 2017-2019 MuK IT GmbH.
#
#    This file is part of MuK Session Store
#    (see https://mukit.at).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

import pickle
import logging
import psycopg2
import functools

from contextlib import closing
from contextlib import contextmanager
from datetime import datetime, date

from werkzeug.contrib.sessions import SessionStore

from odoo.sql_db import db_connect
from odoo.tools import config

_logger = logging.getLogger(__name__)


def retry_database(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        for attempts in range(1, 6):
            try:
                return func(self, *args, **kwargs)
            except psycopg2.InterfaceError as error:
                _logger.warn("SessionStore connection failed! (%s/5)" % attempts)
                if attempts >= 5:
                    raise error

    return wrapper


class PostgresSessionStore(SessionStore):
    def __init__(self, *args, **kwargs):
        super(PostgresSessionStore, self).__init__(*args, **kwargs)
        self.dbname = config.get("session_store_dbname", "session_store")
        self.dbtable = config.get("session_store_dbtable", "odoo_sessions")
        self._setup_database(raise_exception=False)

    def _setup_database(self, raise_exception=True):
        try:
            with db_connect(self.dbname, allow_uri=True).cursor() as cursor:
                cursor.autocommit(True)
                self._create_table(cursor)
        except:
            self._create_database()
            self._setup_database()

    def _create_database(self):
        with db_connect("postgres").cursor() as cursor:
            cursor.autocommit(True)
            cursor.execute(
                """
                CREATE DATABASE {dbname} 
                ENCODING 'unicode'
                TEMPLATE 'template0';
            """.format(
                    dbname=self.dbname
                )
            )

    def _create_table(self, cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS {dbtable} (
                sid varchar PRIMARY KEY,
                write_date timestamp without time zone NOT NULL,
                payload bytea NOT NULL
            );
        """.format(
                dbtable=self.dbtable
            )
        )

    @contextmanager
    def open_cursor(self):
        connection = db_connect(self.dbname, allow_uri=True)
        cursor = connection.cursor()
        cursor.autocommit(True)
        yield cursor
        cursor.close()

    @retry_database
    def save(self, session):
        with self.open_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO {dbtable} (sid, write_date, payload)
                VALUES (%(sid)s, now() at time zone 'UTC', %(payload)s)
                ON CONFLICT (sid)
                DO UPDATE SET payload = %(payload)s, write_date = now() at time zone 'UTC';
            """.format(
                    dbtable=self.dbtable
                ),
                dict(
                    sid=session.sid,
                    payload=psycopg2.Binary(
                        pickle.dumps(dict(session), pickle.HIGHEST_PROTOCOL)
                    ),
                ),
            )

    @retry_database
    def delete(self, session):
        with self.open_cursor() as cursor:
            cursor.execute(
                "DELETE FROM {dbtable} WHERE sid=%s;".format(dbtable=self.dbtable),
                [session.sid],
            )

    @retry_database
    def get(self, sid):
        if not self.is_valid_key(sid):
            return self.new()
        with self.open_cursor() as cursor:
            cursor.execute(
                """
                SELECT payload, write_date 
                FROM {dbtable} WHERE sid=%s;
            """.format(
                    dbtable=self.dbtable
                ),
                [sid],
            )
            try:
                payload, write_date = cursor.fetchone()

                if isinstance(write_date, str):
                    _logger.debug("write_date is str")
                    write_date = datetime.strptime(
                        write_date, '%Y-%m-%d %H:%M:%S.%f')

                if write_date.date() != datetime.today().date():
                    cursor.execute(
                        """
                        UPDATE {dbtable} 
                        SET write_date = now() at time zone 'UTC' 
                        WHERE sid=%s;
                    """.format(
                            dbtable=self.dbtable
                        ),
                        [sid],
                    )
                return self.session_class(pickle.loads(payload), sid, False)
            except Exception as e:
                _logger.exception("Error fetching payload", exc_info=e)
                return self.session_class({}, sid, False)

    @retry_database
    def list(self):
        with self.open_cursor() as cursor:
            cursor.execute("SELECT sid FROM {dbtable};".format(dbtable=self.dbtable))
            return [record[0] for record in cursor.fetchall()]

    @retry_database
    def clean(self):
        with self.open_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM {dbtable} 
                WHERE now() at time zone 'UTC' - write_date > '7 days';
            """.format(
                    dbtable=self.dbtable
                )
            )
