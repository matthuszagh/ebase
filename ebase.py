#!/usr/bin/python

import yaml
import psycopg2
from psycopg2.extensions import AsIs
import fileinput
import sys
import glob
import os
import subprocess
import argparse
import shlex
import csv
import ast
import time
import usb.core
import usb.util
import math


def db_conn():
    """Connect to the electronics inventory database using the credentials in credentials.yml."""
    f = open('/usr/local/bin/ebase_config/credentials.yml', 'r')
    data = yaml.load(f)
    dbname = data['dbname']
    user = data['user']
    conn = psycopg2.connect('dbname={} user={}'.format(dbname, user))
    return conn


def normalize_path(path):
    """Remove trailing '/' from path if it has one."""
    if (path[-1] == '/'):
        return path[0:-1]
    else:
        return path


def postgres_arr_from_str(string):
    """Converts a string with space-delimited values to the array syntax Postgres understands."""
    string = '{' + string.replace(' ', ',') + '}'
    return string


def _parse_bytes(field):
    """
    Convert string represented in Python byte-string literal syntax into a decoded character
    string. Other field types returned unchanged.

    """
    result = field
    try:
        result = ast.literal_eval(field)
    finally:
        return result.decode() if isinstance(result, bytes) else field


def fix_bytes(filename, delimiter=','):
    with open(filename, 'rt') as f:
        yield from (delimiter.join(_parse_bytes(field)
                                   for field in line.split(delimiter))
                    for line in f)


def print_proj_table(tbl):
    """Pretty print Postgres table."""
    # TODO: use "rows, columns = subprocess.check_output(['stty', 'size']).split()"
    # to nicely overflow ref designators based on terminal width.
    if len(tbl) == 3:
        max_width = 0
        for i in tbl:
            num_chars = len(i[0])
            if (num_chars > max_width):
                max_width = num_chars
        for i in tbl:
            print("{mfn:<{mfn_width}}{stock:>{stock_width}}  {ref_designators}".format(
                mfn=i[0], mfn_width=max_width, stock=i[1], stock_width=4, ref_designators=i[2]))
    else:
        print(tbl)


def exec_bash_cmd(cmd):
    """Execute bash command."""
    args = shlex.split(cmd)
    proc = subprocess.call(args)
    return proc


class Scanner():
    """Teemi T22 scanner."""

    def __init__(self):
        self.dev = usb.core.find(idVendor=0x2dd6, idProduct=0x0260)
        if self.dev is None:
            raise ValueError("Device not found.")

        if self.dev.is_kernel_driver_active(0):
            try:
                self.dev.detach_kernel_driver(0)
            except usb.core.USBError as e:
                sys.exit("Could not detach kernel driver.")

        self.dev.set_configuration()
        self.endpoint = self.dev[0][(0, 0)][0]

        try:
            usb.util.claim_interface(self.dev, 0)
        except:
            sys.exit("Could not claim device.")

        self.CODE0 = {
            39: "0",
            30: "1",
            31: "2",
            32: "3",
            33: "4",
            34: "5",
            35: "6",
            36: "7",
            37: "8",
            38: "9",
            44: " ",
            45: "-",
            47: "[",
            48: "]",
            55: ".",
            56: "/"
        }

        self.CODE2 = {
            32: "#",
            39: ")",
            55: ">",
            4: "A",
            5: "B",
            6: "C",
            7: "D",
            8: "E",
            9: "F",
            10: "G",
            11: "H",
            12: "I",
            13: "J",
            14: "K",
            15: "L",
            16: "M",
            17: "N",
            18: "O",
            19: "P",
            20: "Q",
            21: "R",
            22: "S",
            23: "T",
            24: "U",
            25: "V",
            26: "W",
            27: "X",
            28: "Y",
            29: "Z"
        }

    def get_dm(self):
        """Retrieve DataMatrix string from scanner input."""
        s = ""
        while True:
            try:
                self.data = self.dev.read(
                    self.endpoint.bEndpointAddress, self.endpoint.wMaxPacketSize)
                self.idx0 = self.data[0]
                self.idx2 = self.data[2]
                if self.idx0 == 0:
                    if self.idx2 == 0:
                        continue
                    try:
                        c = self.CODE0[self.idx2]
                        s = s + c
                    except:
                        raise ValueError("""Invalid data read from DataMatrix scanner: {}. Update
                        internal database to support this code.""".format(self.data))
                elif self.idx0 == 2:
                    try:
                        c = self.CODE2[self.idx2]
                        s = s + c
                    except:
                        raise ValueError("""Invalid data read from DataMatrix scanner: {}. Update
                        internal database to support this code.""".format(self.data))
                else:
                    raise ValueError("""Invalid data read from DataMatrix scanner: {}. Update
                    internal database to support this code.""".format(self.data))

            except usb.core.USBError as e:
                self.data = None
                if e.args == ('Operation timed out',):
                    continue

            if s.endswith("[CR]"):
                break

        return s

    def parse_dm(self, s):
        """Retrieve MFN and quantity from DataMatrix string."""
        mfn = s.split("[GS]1P")[1].split("[GS]")[0]
        q = s.split("[GS]Q")[1].split("[GS]")[0]
        return mfn, q


class Printer():
    """PT-1230PC printer."""

    def __init__(self):
        self.fname = "tmp.txt"

    def gen_bitmap(self, mfn, size):
        """Write bitmap file recognizable by P-Touch printer for MFN string."""
        if (size <= 0 or size > 64):
            raise ValueError("Size must be between 1 and 64.")

        label_cmd = "textlabel {} --width {}".format(mfn, size)
        args = shlex.split(label_cmd)
        lines = []
        leading_zeros = math.floor((64-size)/2)
        trailing_zeros = 64 - size - leading_zeros
        with open(self.fname, 'w+') as f:
            process = subprocess.call(args, stdout=f)
            f.seek(0)
            text = f.read()
            text = '0'*leading_zeros + \
                text.replace('\n', '0'*trailing_zeros + '\n' + '0' *
                             leading_zeros) + '0'*(size+trailing_zeros) + '\n'
            f.seek(0)
            f.write(text)
            f.truncate()

    def print_label(self, mfn, size):
        """Print label using P-Touch with bitmap in file."""
        self.gen_bitmap(mfn, size)
        cmd = "sudo pt1230 -b -f {}".format(self.fname)
        proc = exec_bash_cmd(cmd)
        clean_f_cmd = "rm {}".format(self.fname)
        exec_bash_cmd(clean_f_cmd)


class DB():
    """Interface to a Postgres database connection."""

    def __init__(self):
        self.conn = db_conn()
        self.cur = self.conn.cursor()
        self.modified = False
        self.print_buf = []

    def __exit__(self):
        self.cur.close()
        self.conn.close()

    def commit(self):
        """Print queries, outputs and commit changes."""
        for i in self.print_buf:
            if i[1] == 'q':  # query
                print("sql> ", i[0])
            elif i[1] == 'o':  # query output
                print('')
                print_proj_table(i[0])
                print('')
            elif i[1] == 'm':  # misc
                print(i[0])
            else:
                raise ValueError("Invalid print data.")

        self.print_buf = []

        if self.modified == True:
            self.confirm_mod()

    def exec_query(self, query, modify=False):
        """Execute Postgres query and display output."""
        if modify:
            self.modified = True

        self.print_buf.append((query, 'q'))
        self.cur.execute(query)
        try:
            fetch_data = self.cur.fetchall()
        except:
            return

        self.print_buf.append((fetch_data, 'o'))
        return fetch_data

    def confirm_mod(self):
        """Prompt the user if the change should be committed."""
        exec_bash_cmd("ebase_config/backup.sh")
        c = input("\nCommit? y/n ")
        if c == 'y':
            self.conn.commit()
        elif c == 'n':
            print("Nothing done.")
            exit(0)
        else:
            print("Must answer y/n.")
            exit(1)

    def wr_csv_data(self, f, name):
        csv_reader = csv.reader(fix_bytes(f))
        for row in csv_reader:
            if row:
                if row[0].isdigit() and row[1]:
                    insert_query = """insert into projects.{0} (mfn, qty, ref_designators) 
                    values ('{1}', {2}, '{3}')""".format(name, row[1], row[2],
                                                         postgres_arr_from_str(row[3]))
                    self.exec_query(insert_query, True)

    def sync_proj_entries(self, proj):
        """
        If an MFN exists in a project table but not in the parts database, add an entry
        for it to the parts db.
        """
        parts = self.exec_query("""select mfn from projects.{0} where not exists (select 1 from parts where
        mfn=projects.{0}.mfn)""".format(proj))
        for part in parts:
            self.exec_query(
                """insert into parts (mfn, stock) values (%s, 0)""", (part[0],))

    def update_part(self, mfn, q):
        """Add stock to an existing part in the parts table."""
        add_query = """update parts set stock=stock+{0} where mfn='{1}'""".format(
            q, mfn)
        self.exec_query(add_query, True)

    def init_part(self, mfn):
        """Add entry to parts database for an mfn."""
        add_query = "insert into parts (mfn, stock) values ('{0}', {1})".format(
            mfn, 0)
        self.exec_query(add_query, True)

    def create_part(self, mfn, q, storage):
        """Create a part in the parts table. The mfn entry must already exist for this to work."""
        update_query = "update parts set stock={0}, storage='{1}' where mfn='{2}'".format(
            q, storage, mfn)
        self.exec_query(update_query, True)

    def find_storage(self):
        """Return the least occupied storage location for a new part."""
        find_store_query = """select storage from parts where storage!='' group by storage order by count(storage), storage
        limit 1"""
        return self.exec_query(find_store_query)[0][0]

    def list_proj(self, args):
        """Query project parts."""
        if not args.o:
            args.o = os.getcwd() + '/' + args.proj + '.csv'

        display_parts_query = """select parts.mfn, qty, ref_designators, storage from parts, projects.{0} where
        parts.mfn = projects.{0}.mfn""".format(args.proj)
        self.exec_query(display_parts_query)

        write_file_query = "COPY ({0}) TO STDOUT WITH CSV HEADER".format(
            display_parts_query)

        with open(args.o, 'w') as f:
            self.cur.copy_expert(write_file_query, f)

        self.commit()

    def create_proj(self, args):
        """Create a project table for a KiCad project."""
        args.proj_dir = normalize_path(args.proj_dir)
        name = glob.glob(args.proj_dir + "/*pro")[0].split("/")[-1][:-4]
        bom_cmd = "kibom --cfg {0}/bom.ini {0}/{1}.xml {0}/tmp.csv".format(
            args.proj_dir, name)
        exec_bash_cmd(bom_cmd)

        drop_table_query = """drop table if exists projects.{0}""".format(name)
        self.exec_query(drop_table_query, True)
        create_table_query = """create table projects.{0} (mfn text not null, qty integer,
        ref_designators text[])""".format(name)
        self.exec_query(create_table_query, True)
        self.wr_csv_data("{}/tmp.csv".format(args.proj_dir), name)
        if self.modified == True:
            self.confirm_mod()

        clean_proj_dir_cmd = "rm -f {}/tmp.csv*".format(args.proj_dir)
        exec_bash_cmd(clean_proj_dir_cmd)
        clean_src_dir_cmd = "rm -f tmp.csv*"
        exec_bash_cmd(clean_src_dir_cmd)

    def scan(self, args):
        """Scan a DataMatrix code and store the component."""
        if os.getuid() != 0:
            raise PermissionError(
                "ebase scan must be run with superuser privileges")
        scanner = Scanner()
        s = scanner.get_dm()
        mfn, q = scanner.parse_dm(s)
        mfn_query = """select storage from parts where mfn='{}'""".format(mfn)

        try:
            storage = self.exec_query(mfn_query)[0][0]
        except:
            self.init_part(mfn)
            storage = None

        if storage != None:
            print("{0} already has storage at location {1}".format(mfn, storage))
            self.update_part(mfn, q)
        else:
            storage = self.find_storage()
            printer = Printer()
            printer.print_label(mfn, 20)
            self.create_part(mfn, q, storage)

        self.commit()

    def homeless(self, args):
        """Show parts in the parts database without a storage location."""
        query = """select * from parts where stock > 0 and (storage = '') is not false group by mfn"""
        self.exec_query(query)
        self.commit()

    def build(self, args):
        """Build a project and decrement the parts stock."""
        query_list = """select parts.mfn, stock from parts, projects.{0} where parts.mfn = projects.{0}.mfn""".format(
            args.proj)
        lst_old = self.exec_query(query_list)
        self.exec_query("""drop table if exists tmp""")
        self.exec_query("""create table tmp (mfn text, stock int)""", True)
        self.exec_query("""insert into tmp select parts.mfn, stock - qty from parts, projects.{0}
        where parts.mfn = projects.{0}.mfn""".format(args.proj), True)
        self.exec_query("""update tmp set stock=0 where stock<0""", True)
        self.exec_query(
            """update parts set stock = tmp.stock from tmp where parts.mfn=tmp.mfn""", True)
        self.exec_query("""drop table tmp""", True)
        lst_new = self.exec_query(query_list)
        inc = 0
        for i in lst_old:
            self.print_buf.append(
                ("{0:<25}{1:>4}   ->{2:>4}".format(i[0], i[1], lst_new[inc][1]), 'm'))
            inc = inc + 1

        self.commit()

    def missing(self, args):
        """
        Display project parts with insufficient stock and optionally generate a CSV file that can be
        uploaded to Digi-Key.
        """
        self.sync_proj_entries(args.proj)
        self.exec_query("""create table tmp(mfn text not null, qty integer)""")
        self.exec_query("""insert into tmp select mfn, qty - (select stock from parts where mfn = projects.{0}.mfn) from
        projects.{0} where qty > (select stock from parts where mfn = projects.{0}.mfn)""".format(args.proj))
        self.exec_query("""select * from tmp""")

        if args.o:
            with open(args.o, 'w') as f:
                self.cur.copy_to(f, 'tmp', sep=',')

        self.exec_query("""drop table tmp""")
        self.commit()


if __name__ == '__main__':
    db = DB()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # build
    parser_build = subparsers.add_parser(
        'build', help="Build a project and decrement the parts stock.")
    parser_build.add_argument("proj", help="""The project to build.""")
    parser_build.set_defaults(func=db.build)

    # create_proj
    parser_create_proj = subparsers.add_parser(
        'create_proj', help="""Create a table in the electronics_inventory database for a project, or replace the table if it
        already exists.""")
    parser_create_proj.add_argument(
        "proj_dir", help="""The full directory containing the KiCad hardware files for the relevant project.""")
    parser_create_proj.add_argument("-n", help="""Name for the project. If one is not supplied then
    the KiCad project name will be given. All hyphens will be replaced with underscores for
    compatibility with Postgres.""")
    parser_create_proj.set_defaults(func=db.create_proj)

    # homeless
    parser_homeless = subparsers.add_parser(
        'homeless', help="Display parts without a storage location.")
    parser_homeless.set_defaults(func=db.homeless)

    # list_proj
    parser_list_proj = subparsers.add_parser(
        'list_proj', help='Writes a csv file with the collection of parts needed for a design.')
    parser_list_proj.add_argument(
        "proj", help="""The project whose parts should be displayed. This must exactly match the project as it appears
        in the 'projects' schema.""")
    parser_list_proj.add_argument(
        "-o", help="""The output csv file to write.""")
    parser_list_proj.set_defaults(func=db.list_proj)

    # missing
    parser_missing = subparsers.add_parser('missing', help="""Displays the parts in a project that
    are missing from the parts inventory. This can also be used to generate a csv file that can
    be uploaded to Digi-Key BOM in order to automate ordering missing parts.""")
    parser_missing.add_argument("proj", help="""Project.""")
    parser_missing.add_argument("-o", help="""Output CSV file.""")
    parser_missing.set_defaults(func=db.missing)

    # scan
    parser_store = subparsers.add_parser(
        'scan', help="""Scan a DataMatrix code and store the component. If storage already exists for the component, the
        location is specified so component can be stored there. If storage does not exist, allocate
        it and print a label. The parts table stock is updated in both scenarios.""")
    parser_store.set_defaults(func=db.scan)

    args = parser.parse_args()
    args.func(args)
