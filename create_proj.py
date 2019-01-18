#!/usr/bin/python

# 3rd party modules
import sys, getopt
import glob, os
import subprocess
import csv
import ast
import psycopg2
# internal modules
import ebase

def help():
    """Print a help message to the console output."""
    print("""Create a table in the electronic-inventory database for a project, or replace the table if it already exists.\nWARNING! You must first run bom2csv from Eeschema (in the bom generation script). This should be easy to incorporate into here (and should be done in the future), but I haven't done it yet.""")
    print("Usage: create_proj.py [options]")
    print("\t-h")
    print("\t\tDisplay help.\n")
    print("\t-p proj_dir")
    print("\t\tThe full directory containing the KiCad hardware files for the relevant project.\n")
    print("\t-n name")
    print("\t\tName for the project. If one is not supplied then the KiCad project name will be given. All hyphens will be replaced with underscores for compatibility with Postgres.")
    
def postgres_arr_from_str(string):
    """Converts a string with space-delimited values to the array syntax Postgres understands."""
    string = '{' + string.replace(' ', ',') + '}'
    return string

def _parse_bytes(field):
    """ Convert string represented in Python byte-string literal syntax into a
    decoded character string. Other field types returned unchanged.
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
 
def wr_csv_data(f, name, cur):
    csv_reader = csv.reader(fix_bytes(f))
    for row in csv_reader:
        if row:
            if row[0].isdigit() and row[1]:
                insert_query = """insert into projects.{0} (mfn, qty, ref_designators) 
                values ('{1}', {2}, '{3}')""".format(name, row[1], row[2],
                                                 postgres_arr_from_str(row[3]))
                cur.execute(insert_query)
    
def main(argv, conn, cur):
    proj_dir = ''
    name = ''

    try:
        opts, _ = getopt.getopt(argv, "hp:n:")
    except getopt.GetoptError:
        help()
        exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            exit(0)
        elif opt == '-p':
            proj_dir = arg
        elif opt == '-n':
            name = arg

    if proj_dir == '':
        print("-p is required.")
        exit(1)

    if proj_dir[0] != '/':
        print("Must pass an absolute directory.")
        exit(1)

    if proj_dir[-1] != '/':
        proj_dir = proj_dir + '/'

    src_dir = os.path.dirname(os.path.realpath(__file__))
    if name == '':
        os.chdir(proj_dir)
        f = glob.glob("*.pro")[0][:-4]
        name = f.replace("-", "_")
        os.chdir(src_dir)

    subprocess.call(["/home/matt/developer/src/third-party/KiBoM/KiBOM_CLI.py", "--cfg", "{0}/bom.ini".format(src_dir), "{0}{1}.xml".format(proj_dir, f), "{0}/tmp.csv".format(src_dir)])

    cur.execute("""drop table if exists projects.{0}""".format(name))
    cur.execute("""create table projects.{0} (mfn text not null, qty integer,
    ref_designators text[])""".format(name))

    wr_csv_data('tmp_.csv', name, cur)

    cur.execute("""select * from projects.{0}""".format(name))
    ebase.print_proj_table(cur.fetchall())

    c = input('\nCommit? y/n ')
    if c == 'y':
        conn.commit()
    elif c == 'n':
        print("Nothing done.")
        ebase.clean_csv(src_dir)
        exit(0)
    else:
        print("Must answer y/n.")
        ebase.clean_csv(src_dir)
        exit(1)


if __name__ == "__main__":
    conn = ebase.db_conn()
    cur = conn.cursor()
    main(argv=sys.argv[1:], conn=conn, cur=cur)
    cur.close()
    conn.close()
