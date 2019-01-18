#!/usr/bin/python

# 3rd party modules
import sys, getopt
import psycopg2
# internal modules
import ebase

def help():
    """Print a help message to the console output."""
    print("""Decrements the parts used in a project from the parts database. This is used when a project has been built and you wish to update the stock.\n""")
    print("Usage: build.py [options]")
    print("\t-h")
    print("\t\tDisplay help.\n")
    print("\t-p project")
    print("\t\tThe project whose parts should be removed from storage.\n")

def main(argv, conn, cur):
    proj = ''

    try:
        opts, _ = getopt.getopt(argv, "hp:")
    except getopt.GetoptError:
        help()
        exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            exit(0)
        elif opt == '-p':
            proj = arg

    if proj == '':
        print("-p is required.")
        exit(1)

    query_list = """select parts.mfn, stock from parts, projects.{0} where parts.mfn = projects.{0}.mfn""".format(proj)
    cur.execute(query_list)
    lst_old = cur.fetchall()
    cur.execute("""drop table if exists tmp""")
    cur.execute("""create table tmp (mfn text, stock int)""")
    cur.execute("""insert into tmp select parts.mfn, stock - qty from parts, projects.{0} where parts.mfn = projects.{0}.mfn""".format(proj))
    cur.execute("""update tmp set stock=0 where stock<0""")
    cur.execute("""update parts set stock = tmp.stock from tmp where parts.mfn=tmp.mfn""")
    cur.execute("""drop table tmp""")
    cur.execute(query_list)
    lst_new = cur.fetchall()
    inc = 0
    for i in lst_old:
        print("{0:<20}{1:>4}   ->{2:>4}".format(i[0], i[1], lst_new[inc][1]))
        inc = inc + 1

    c = input('\nCommit? y/n ')
    if c == 'y':
        conn.commit()
    elif c == 'n':
        print("Nothing done.")
        exit(0)
    else:
        print("Must answer y/n.")
        exit(1)

if __name__ == "__main__":
    conn = ebase.db_conn()
    cur = conn.cursor()
    main(argv=sys.argv[1:], conn=conn, cur=cur)
    cur.close()
    conn.close()
