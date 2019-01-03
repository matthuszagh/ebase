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

def help():
    """Print a help message to the console output."""
    print("Usage: store.py [options]")
    print("\t-h")
    print("\t\tDisplay help.\n")
    print("\t-s storage")
    print("\t\tSpecifies a desired storage location. If none is specified, one will be assigned according to capacity.\n")
    print("\t-m mfn")
    print("""\t\tSpecify the MFN of the device to set a storage location for. There must already be
    \t\tan entry in the parts database for this device.\n""")

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
