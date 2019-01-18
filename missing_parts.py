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
    print("""Displays the parts in a project that are missing from the parts inventory.
    This can also be used to generate a csv file that can be uploaded to Digi-Key BOM
    in order to automate ordering missing parts.""")
    print("Usage: missing_parts.py [options]")
    print("\t-h")
    print("\t\tDisplay help.\n")
    print("\t-p proj")
    print("\t\tThe name of the project table.\n")
    print("\t-o out_file")
    print("""\t\tWrites the result to an output csv file that can be uploaded to Digi-Key.
    If this option is not provided, the missing parts will simply be written to the console.""")
    
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
    proj = ''
    out = ''

    try:
        opts, _ = getopt.getopt(argv, "hp:o:")
    except getopt.GetoptError:
        help()
        exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            exit(0)
        elif opt == '-p':
            proj = arg
        elif opt == '-o':
            out = arg

    if proj == '':
        print("-p is required.")
        exit(1)

    ebase.sync_proj_entries(proj, cur)
    c = input('\nCommit? y/n ')
    if c == 'y':
        conn.commit()
    elif c == 'n':
        print("Nothing done.")
        exit(0)
    else:
        print("Must answer y/n.")
        exit(1)

    cur.execute("""create table tmp(mfn text not null, qty integer)""")
    cur.execute("""insert into tmp select mfn, qty - (select stock from parts 
    where mfn = projects.{0}.mfn) from projects.{0} where qty > 
    (select stock from parts where mfn = projects.{0}.mfn)""".format(proj))
    with open('{0}_digikey.csv'.format(proj), 'w') as f:
        cur.copy_to(f, 'tmp', sep=',')
    cur.execute("""drop table tmp""")

    src_dir = os.path.dirname(os.path.realpath(__file__))
    ebase.clean_csv(src_dir)

if __name__ == "__main__":
    conn = ebase.db_conn()
    cur = conn.cursor()
    main(argv=sys.argv[1:], conn=conn, cur=cur)
    cur.close()
    conn.close()
