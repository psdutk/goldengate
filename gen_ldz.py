#!/usr/bin/env python

"""
Script to generate sql for the LandingZone
"""

import argparse
import sys


from common import common
from lazydb import lazydb
from tables import tables
from lobs import lobs
from constants import VALID_ENVS

"""
Constants
"""
FILTER_STEPS = ["create_tables", "tables_add_ons", "drop_lobs"]

"""
"""


class LdzGenerator:
    def __init__(self, db_conn, tables_fn, lobs_fn, verbose):
        self.db_conn = db_conn
        self.tables_obj = tables.Tables(tables_fn)
        self.lobs_obj = lobs.Lobs(lobs_fn)
        self.verbose = verbose

    """
    """

    def load_static_data(self):
        self.tables_obj.load_tables_into_db(self.db_conn)
        self.lobs_obj.load_lobs_into_db(self.db_conn)

    """
    """

    def gen_tables(self, filter_table):
        for table in self.tables_obj.tables:
            if not filter_table or filter_table == table.table_name:
                row = self.db_conn.execute_sql(
                    sql_fn="sql/gen_create_table.sql",
                    fetch_only_one=True,
                    bind_data={"owner": table.owner, "table_name": table.table_name},
                )
                if not row:
                    sys.stderr.write(
                        f"Table: {table.owner}.{table.table_name} was not found, please check"
                    )
                    sys.exit(1)
                (ddl,) = row
                sys.stdout.write(ddl + ";\n")

    """
    """

    def gen_tables_addons(self, filter_table):
        j2_gen_table_addons = common.read_j2_template("sql/gen_table_addons.sql.j2")
        for table in self.tables_obj.tables:
            if not filter_table or filter_table == table.table_name:
                sys.stdout.write("\n")
                sys.stdout.write(
                    j2_gen_table_addons.render({"table_name": table.table_name})
                )

    """
    generate DROP COLUMN for all lob columns (data_type IN ('CLOB', 'BLOB') not included in the file lobs.csv
    """

    def gen_drop_lobs(self, filter_table):
        for table in self.tables_obj.tables:
            if not filter_table or filter_table == table.table_name:
                rows = self.db_conn.execute_sql(
                    sql_fn="sql/get_lob_columns.sql",
                    bind_data={"owner": table.owner, "table_name": table.table_name},
                )
                for (column_name,) in rows:
                    if not self.lobs_obj.is_member(
                        table.owner, table.table_name, column_name
                    ):
                        sys.stdout.write("\n")
                        sys.stdout.write(
                            f"ALTER TABLE {table.table_name} DROP COLUMN {column_name};"
                        )


"""
do_work
"""


def do_work(
    db_config,
    tables_fn,
    lobs_fn,
    args,
):
    # create a copy for lazydb (owner is not needed for the connection)
    if "owner" in db_config:
        db_config_copy = dict(db_config)
        del db_config_copy["owner"]
        db_conn = lazydb.LazyDb(db_config_copy)
    else:
        db_conn = lazydb.LazyDb(db_config)
    #
    ldz_generator = LdzGenerator(
        db_conn,
        tables_fn,
        lobs_fn,
        args.verbose,
    )
    if not args.filter_step or args.filter_step == "create_tables":
        ldz_generator.gen_tables(args.filter_table)
    if not args.filter_step or args.filter_step == "tables_add_ons":
        ldz_generator.gen_tables_addons(args.filter_table)
    if not args.filter_step or args.filter_step == "drop_lobs":
        ldz_generator.gen_drop_lobs(args.filter_table)


"""
initializes argparse
"""


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
Generates the SQLs to create all objects in the landingzone database
""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Example 1: generates the SQLs for the LandingZone on prod

    ./gen_ldz.py config.json prod

Example 2: generates the SQLs for the LandingZone on prod

    ./gen_ldz.py config.json prod
""",
    )
    parser.add_argument("config_file", help="config file (json)")
    parser.add_argument("env", choices=VALID_ENVS, help="environment")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose")
    # parser.add_argument(
    #     "--delta",
    #     action="store_true",
    #     help="generates only the missing tables at the target",
    # )
    # parser.add_argument(
    #     "--dryrun",
    #     action="store_true",
    #     help="tests the execution, does't makes any modification at the database",
    # )
    parser.add_argument(
        "--filter_step",
        choices=FILTER_STEPS,
        help="only the given step will be generated",
    )
    parser.add_argument(
        "--filter_table", help="only the SQLs for the given table will be generated"
    )
    parser.add_argument("--pwd_db", help="Password for source db")
    return parser


"""
main
"""


def main():
    parser = init_argparse()
    args = parser.parse_args()
    config_file = args.config_file
    env = args.env
    config = common.read_json(config_file)[env]
    #
    if args.verbose:
        print(f"Filter table {args.filter_table}")
        print(f"Filter step {args.filter_step}")

    #
    source_db = config["source_db"]
    if args.pwd_db:
        source_db["password"] = args.pwd_db
    do_work(
        source_db,
        config["tables_file"],
        config["lobs_file"],
        args,
    )


"""
"""
if __name__ == "__main__":
    main()
