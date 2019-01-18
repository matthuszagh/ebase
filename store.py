#!/usr/bin/python

# 3rd party modules
import sys, getopt
import psycopg2
# internal modules
import ebase

def help():
    """Print a help message to the console output."""
    print("""Specifies the storage location for a device in the parts database. This should only be used
    for parts that don't already have an assigned location. If you wish the change the location of a
    part you should use update.py instead.\n""")
    print("Usage: store.py [options]")
    print("\t-h")
    print("\t\tDisplay help.\n")
    print("\t-s storage")
    print("\t\tSpecifies a desired storage location. If none is specified, one will be assigned according to capacity.\n")
    print("\t-m mfn")
    print("""\t\tSpecify the MFN of the device to set a storage location for. There must already be
    \t\tan entry in the parts database for this device.\n""")

def select_storage(cur, mfn):
    """Use the storage location with the least number of distinct parts."""
    cur.execute("select storage from parts where mfn=%s;", (mfn,))
    storage = cur.fetchall()[0]
    storage = storage[0]
    if storage != None:
        print("Part already has storage. If you'd like to update the storage location, use update.py instead.")
        sys.exit(0)

    cur.execute("select storage from parts where storage!='' group by storage order by count(storage), storage limit 1")
    ret = cur.fetchall()[0]
    ret = ret[0]
    return ret

def main(argv, conn, cur):
    storage = ''
    mfn = ''

    try:
        opts, _ = getopt.getopt(argv, "hsm:")
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-s':
            storage = arg
        elif opt == '-m':
            mfn = arg

    if mfn == '':
        print("-m is required.")
        sys.exit(1)

    if storage == '':
        storage = select_storage(cur, mfn)
        print("Storage location: {}".format(storage))

    ebase.update(conn=conn, cur=cur, mfn=mfn, col='storage', val=storage)

if __name__ == "__main__":
    conn = ebase.db_conn()
    cur = conn.cursor()
    main(argv=sys.argv[1:], conn=conn, cur=cur)
    cur.close()
    conn.close()
