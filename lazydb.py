#!/usr/bin/env python

import oracledb

from getpass import getpass
from pprint import pprint as pp
from common import common


"""
Constants
"""
LOB_DATATYPES = ["CLOB", "BLOB"]
DBMS_OUTPUT_CHUNK_SIZE = 10


"""
"""


def convert_script2sql_commands(sql_script, sep=";"):
    all_sqls = sql_script.split(sep)
    return [sql for sql in all_sqls if not sql.isspace()]


"""
"""


def convert_sql_file2sql_commands(script_fn, sep=";"):
    with open(script_fn) as fh:
        return convert_script2sql_commands(fh.read(), sep)


"""
"""


def read_sql_file(sql_fn):
    with open(sql_fn) as fh:
        sql = fh.read()
    return sql


"""
"""


class LazyDb:
    """
    class variable
    """

    oracle_init_done = False

    """
    """

    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = self.connect()

    """
    """

    def __enter__(self):
        return self

    """
    """

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self.conn:
            self.conn.close()

    """
    """

    def set_db_mode(self):
        oracledb.AUTH_MODE_DEFAULT
        if "db_role" in self.db_config:
            if self.db_config["db_role"] == "SYSDBA":
                self.db_config["mode"] = oracledb.AUTH_MODE_SYSDBA
                del self.db_config["db_role"]
            else:
                raise Exception(f"db_role: {self.db_config['db_role']} not implemented")

    """
    """

    def set_db_pwd(self):
        if "password" not in self.db_config and "user" in self.db_config:
            self.db_config["password"] = getpass(
                f"Enter password for {self.db_config['user']}@{self.db_config['dsn']}:"
            )

    """
    """

    def init_oracle_client(self):
        if "config_dir" in self.db_config:
            oracledb.init_oracle_client(config_dir=self.db_config["config_dir"])
            del self.db_config["config_dir"]
        else:
            oracledb.init_oracle_client()

    """
    """

    def connect(self):
        self.set_db_pwd()
        self.set_db_mode()
        if not LazyDb.oracle_init_done:
            self.init_oracle_client()
            LazyDb.oracle_init_done = True
        self.conn = oracledb.connect(**self.db_config)

        """
        output_type_handler: to map CLOB to LONG
        """

        def output_type_handler(cursor, name, default_type, size, precision, scale):
            if default_type == oracledb.DB_TYPE_CLOB:
                return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)

        self.conn.outputtypehandler = output_type_handler
        return self.conn

    """
    """

    def commit(self):
        self.conn.commit()

    """
    """

    def rollback(self):
        self.conn.rollback()

    """
    """

    def gettype(self, type_name):
        return self.conn.gettype(type_name)

    """
    """

    def get_cursor(self):
        return self.conn.cursor()

    """
    """

    def execute_sql_script(self, sql_script=None, sql_script_fn=None, sep=";"):
        assert sql_script or sql_script_fn, "at least one must be not given"
        if sql_script:
            sqlCommands = convert_script2sql_commands(sql_script, sep)
        else:
            sqlCommands = convert_sql_file2sql_commands(sql_script_fn, sep)
        with self.get_cursor() as cursor:
            for sql in sqlCommands:
                if sql:
                    try:
                        cursor.execute(sql)
                    except oracledb.Error as e:
                        (error_obj,) = e.args
                        print(f"Stmt failed:{sql}")
                        print("Error Code:", error_obj.code)
                        print("Error Message:", error_obj.message)
                        raise e

    """
    """

    def execute_sql(
        self,
        sql=None,
        sql_fn=None,
        sql_j2_template_fn=None,
        rendering_data=None,
        fetch_only_one=False,
        fetch_all=True,
        bind_data=None,
        print_dbms_output=False,
        dbms_output=[],
    ):
        if sql:
            None
        elif sql_fn:
            sql = read_sql_file(sql_fn)
        elif sql_j2_template_fn:
            j2_template = common.read_j2_template(sql_j2_template_fn)
            sql = j2_template.render(rendering_data)
        else:
            raise Exception("no sql given")

        with self.get_cursor() as cursor:
            if print_dbms_output:
                cursor.callproc("dbms_output.enable", [None])
            try:
                if bind_data:
                    cursor.execute(sql, bind_data)
                else:
                    cursor.execute(sql)
                if fetch_only_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                if print_dbms_output:
                    lines_var = cursor.arrayvar(str, DBMS_OUTPUT_CHUNK_SIZE)
                    num_lines_var = cursor.var(int)
                    num_lines_var.setvalue(0, DBMS_OUTPUT_CHUNK_SIZE)
                    while True:
                        cursor.callproc(
                            "dbms_output.get_lines", (lines_var, num_lines_var)
                        )
                        num_lines = num_lines_var.getvalue()
                        lines = lines_var.getvalue()[:num_lines]
                        [dbms_output.append(line) for line in lines if line]
                        if num_lines < DBMS_OUTPUT_CHUNK_SIZE:
                            break
            except oracledb.Error as e:
                print(sql)
                if bind_data:
                    pp(bind_data)
                raise e
