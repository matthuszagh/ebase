#!/usr/bin/python

# 3rd party modules
import sys, getopt
import psycopg2
# internal modules
import ebase

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
    
def main(argv, cur):
    storage = ''
    mfn = ''

    try:
        opts, args = getopt.getopt(argv, "hsm:")
    except getopt.GetoptError:
        ebase.help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            ebase.help()
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
    main(sys.argv[1:], cur)
    cur.close()
    conn.close()
