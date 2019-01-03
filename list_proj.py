#!/usr/bin/python

# 3rd party modules
import sys, getopt
import psycopg2
# internal modules
import ebase

def help():
    """Print a help message to the console output."""
    print("Writes a csv file with the collection of parts needed for a design.\n")
    print("Usage: list_proj.py [options]")
    print("\t-h")
    print("\t\tDisplay help.\n")
    print("\t-p project")
    print("""\t\tThe project whose parts should be displayed. This must exactly match the project as it appears
    \t\tin the 'projects' schema.\n""")
    print("\t-o out_file")
    print("""\t\tThe output csv file to write. If none is specified, it will be written in the home directory
    \t\twith the name of the project.\n""")

def main(argv, conn, cur):
    proj = ''
    out_f = ''
    
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
            out_f = arg

    if proj == '':
        print("-p is required.")
        exit(1)

    if out_f == '':
        out_f = '/home/matt/' + proj + '.csv'

    query = """select parts.mfn, qty, ref_designators, storage from parts, projects.{0} where
    parts.mfn = projects.{0}.mfn""".format(proj)

    outputquery = "COPY ({0}) TO STDOUT WITH CSV HEADER".format(query)

    with open(out_f, 'w') as f:
        cur.copy_expert(outputquery, f)

if __name__ == "__main__":
    conn = ebase.db_conn()
    cur = conn.cursor()
    main(argv=sys.argv[1:], conn=conn, cur=cur)
    cur.close()
    conn.close()
