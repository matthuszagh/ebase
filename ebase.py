import yaml
import psycopg2
from psycopg2.extensions import AsIs
import fileinput
import sys

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
