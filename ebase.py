import yaml
import psycopg2
from psycopg2.extensions import AsIs
import fileinput
import sys
import glob
import os
import subprocess


def db_conn():
    """Connect to the electronics inventory database using the credentials in credentials.yml."""
    f = open('credentials.yml', 'r')
    data = yaml.load(f)
    dbname = data['dbname']
    user = data['user']
    conn = psycopg2.connect('dbname={} user={}'.format(dbname, user))
    return conn


def update(conn, cur, mfn, col, val):
    cur.execute("update parts set %s=%s where mfn=%s;", (AsIs(col), val, mfn))
    print("Updated entry:")
    cur.execute("select * from parts where mfn=%s;", (mfn,))
    print(cur.fetchall())
    print("")
    c = input('Commit? y/n ')
    if c == 'y':
        conn.commit()
    elif c == 'n':
        print("Nothing done.")
        exit(0)
    else:
        print("Must answer y/n.")
        exit(1)


def print_proj_table(tbl):
    """Pretty print Postgres table."""
    for i in tbl:
        print("{0:<20}{1:>4}  {2}".format(i[0], i[1], i[2]))


def clean_csv(src_dir):
    subprocess.call(
        ["rm", "-f", "{0}/tmp_.csv".format(src_dir), "{0}/tmp_.csv.tmp".format(src_dir)])


def sync_proj_entries(proj, cur):
    """
    If an MFN exists in a project table but not in the parts database, add an entry
    for it to the parts db.
    """
    cur.execute("""select mfn from projects.{0} where not exists
    (select 1 from parts where mfn=projects.{0}.mfn)""".format(proj))
    parts = cur.fetchall()
    print("rows inserted:")
    for part in parts:
        cur.execute(
            """insert into parts (mfn, stock) values (%s, 0)""", (part[0],))
        cur.execute("""select * from parts where mfn=%s""", (part[0],))
        print(cur.fetchone())


def csv_remove_header(f):
    """Remove header (first line) from file."""
    with open(f, 'r') as fin:
        data = fin.read().splitlines(True)
    with open(f, 'w') as fout:
        fout.writelines(data[1:])


def csv_remove_last_line(f):
    """Remove last line from file."""
    with open(f, 'r') as fin:
        data = fin.read().splitlines(True)
    with open(f, 'w') as fout:
        fout.writelines(data[:-1])


def csv_remove_quotes(f):
    """Remove quotes from csv file."""
    with open(f, 'r') as fin:
        data = fin.read()
        data = data.replace("\"", "")
    with open(f, 'w') as fout:
        fout.write(data)
