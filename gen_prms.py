#!/usr/bin/env python

"""
Script to generate the files for  
"""

from pprint import pprint as pp

import argparse

from common import common
from lazydb import lazydb
from tables import tables
from lobs import lobs

from constants import VALID_ENVS

"""
"""


class InsufficientFilesError(Exception):
    """Raised when there are not enough files provided to accommodate the text."""

    pass


class ExcessiveFilesWarning(Warning):
    """Raised when there are more files provided than necessary."""

    pass


"""
"""


class PrmGenerator:
    """ """

    def __init__(
        self,
        process_type: str,
        config: dict[str, any],
        source_db_conn: lazydb.LazyDb,
        verbose: bool = False,
    ):
        self.process_type = process_type
        self.verbose = verbose
        #
        self.source_db_config = config["source_db"]
        self.target_db_config = config["target_db"]
        self.process_config = config["processes"][process_type]
        self.genfetchcols = True
        if "opts" in config["processes"][process_type]:
            if "nofetchcols" in config["processes"][process_type]["opts"]:
                self.genfetchcols = False
        #
        if source_db_conn:
            self.source_db_conn = source_db_conn
        else:
            self.source_db_conn = lazydb.LazyDb(self.source_db_config)

        self.tables = tables.Tables(config["tables_file"])
        self.lobs = lobs.Lobs(config["lobs_file"])

    """
    """

    def generate_process_prm(self):
        template_name = self.process_config["template"]["process"]
        j2_process_template = common.read_j2_template(template_name)
        common.write_j2_template(
            self.process_config["prm_file_name"],
            j2_process_template,
            self.process_config,
        )

    """
    """

    def exec_sql_get_table_columns(self, table: tables.Table) -> list:
        sql = """
SELECT column_name, data_type, data_length
  FROM dba_tab_columns
 WHERE owner = :owner
   AND table_name = :table_name
"""
        rows = self.source_db_conn.execute_sql(
            sql=sql,
            bind_data={"owner": table.owner, "table_name": table.table_name},
        )
        return rows

    """
    returns the list of column names that require a fetchcol
    """

    def get_fetchcols(self, table: tables.Table) -> list:
        fetchcols = []
        columns = self.exec_sql_get_table_columns(table)
        if self.verbose:
            print(f"getting columns for {table.owner}.{table.table_name}")
            print("Columns:")
            pp(columns)
        for column_name, data_type, data_length in columns:
            if (data_type == "RAW" or data_type == "VARCHAR2") and data_length > 4000:
                if self.verbose:
                    print(
                        f"Column: {column_name} is {data_type} has data_lenght {data_length} bigger than 4000"
                    )
                fetchcols.append(column_name)
            elif data_type in lazydb.LOB_DATATYPES and self.lobs.is_member(
                table.owner, table.table_name, column_name, data_type
            ):
                if self.verbose:
                    print(
                        f"Including column: {column_name} with data_type: {data_type} from table: {table.owner}.{table.table_name} because is in the lobs file"
                    )
                fetchcols.append(column_name)
        return fetchcols

    """
    """

    def gen_table_mapping(self, table: tables.Table) -> dict[str, any]:
        table_mapping = {
            **{
                "source_db": self.source_db_config["dsn"],
                "target_db": self.target_db_config["dsn"],
                "target_owner": self.target_db_config["owner"],
            },
            **{"source_owner": table.owner, "table_name": table.table_name},
        }
        if self.process_type == "extract" and self.genfetchcols:
            cols = self.get_fetchcols(table)
            if cols:
                table_mapping["fetchcols"] = ",FETCHCOLS(" + ",".join(cols) + ")"
        return table_mapping

    """
    """

    def write_tables_prm(self, table_prm_files: list[str], content: list[str]):
        current_chunk = []
        line_count = 0
        file_index = 0
        max_number_lines = self.process_config[
            "max_number_lines_per_default_tables_prm"
        ]
        # Calculate the total number of lines in content
        total_lines = sum(len(text.splitlines()) for text in content)

        # Calculate the required number of files based on the total lines
        required_files = (total_lines // max_number_lines) + (
            1 if total_lines % max_number_lines > 0 else 0
        )

        # Check if there are enough files and if there are too many files
        if required_files > len(table_prm_files):
            raise InsufficientFilesError(
                f"Not enough files provided. Required: {required_files}, Provided: {len(table_prm_files)} for process: {self.process_config['process_name']} "
            )
        if required_files < len(table_prm_files):
            raise ExcessiveFilesWarning(
                f"There are {len(table_prm_files) - required_files} unused files provided for process: {self.process_config['process_name']}"
            )

        for text in content:
            # Split the current string into lines
            lines = text.splitlines()
            num_lines = len(lines)

            # Check if adding this element would exceed the limit
            if line_count + num_lines > max_number_lines:
                # Write the current chunk to the next file if available
                if file_index < len(table_prm_files):
                    common.write_text_to_file(
                        table_prm_files[file_index], "\n".join(current_chunk)
                    )
                    # Prepare for the next chunk
                    current_chunk = []
                    line_count = 0
                    file_index += 1
                else:
                    print(
                        f"Warning: No more files available to write chunk {file_index + 1}"
                    )
                    break  # Stop processing if there are no more files

            # Add the lines of the current element to the current chunk
            current_chunk.extend(lines)
            line_count += num_lines

        # Write any remaining lines in the current chunk to a file
        if current_chunk and file_index < len(table_prm_files):
            common.write_text_to_file(
                table_prm_files[file_index], "\n".join(current_chunk)
            )

    """
    generates the prm for the tables, for all tables
    """

    def generate_process_tables_prm(self):
        template_name = self.process_config["template"]["process_tables"]
        j2_table_template = common.read_j2_template(template_name)
        prm_tables_content = []
        for table in self.tables.tables:
            table_mapping = self.gen_table_mapping(table)
            prm_tables_content.append(j2_table_template.render(table_mapping))
        # for backward compatibility, if prm_table_file_name containts only a file, make a list of it
        if isinstance(self.process_config["prm_table_file_name"], str):
            prm_table_file_names = [self.process_config["prm_table_file_name"]]
        else:
            prm_table_file_names = self.process_config["prm_table_file_name"]
        self.write_tables_prm(prm_table_file_names, prm_tables_content)


"""
initializes argparse
"""


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generates all prm files for Oracle Goldengate"
    )
    parser.add_argument("config_file", help="config file (json)")
    parser.add_argument("env", choices=VALID_ENVS, help="environment")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose")
    parser.add_argument("--pwd_source_db", help="Password for source db")
    return parser


"""
gen_prms
"""


def gen_prms(
    config: dict[str:any], env: str, pwd_source_db: str = None, verbose: bool = False
):
    config_env = config[env]
    if pwd_source_db:
        config_env["source_db"]["password"] = pwd_source_db
    source_db_conn = lazydb.LazyDb(config_env["source_db"])
    for process_type in config_env["processes"]:
        enrich_process_config(
            config, env, process_type, config_env["processes"][process_type]
        )
        if verbose:
            print(f"process: {process_type}")
            pp(config_env["processes"][process_type])
        process_prm_generator = PrmGenerator(
            process_type,
            config_env,
            source_db_conn,
            verbose,
        )
        process_prm_generator.generate_process_tables_prm()
        process_prm_generator.generate_process_prm()


"""
do_work
"""


def do_work(args):
    config = common.read_json(args.config_file)
    gen_prms(config, args.env, args.pwd_source_db, args.verbose)


"""
"""


def enrich_process_config(config, env, process, process_config):
    # add env
    process_config["env"] = env
    # trail info is not at the process level, but one level higher
    process_config["trail"] = config[env]["trail"]
    # template can be at the process level, otherwise take the default template
    if "template" not in process_config:
        process_config["template"] = config["default_templates"][process]
    # max_number_lines_per_default_tables_prm can be at the process level, otherwise take the default template
    if "max_number_lines_per_default_tables_prm" not in process_config:
        process_config["max_number_lines_per_default_tables_prm"] = config[
            "default_max_number_lines_per_default_tables_prm"
        ]


"""
main
"""


def main():
    parser = init_argparse()
    args = parser.parse_args()
    do_work(args)


"""
"""
if __name__ == "__main__":
    main()
