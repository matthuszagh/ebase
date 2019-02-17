#!/usr/bin/python

# 3rd party modules
import argparse
import psycopg2
# internal modules
import ebase


if __name__ == '__main__':
    conn = ebase.db_conn()
    cur = conn.cursor()

    parser = argparse.ArgumentParser(
        description="Imports parts from a Digi-Key csv file to the parts database.")
    parser.add_argument("file", help="csv file to import",
                        default="/home/matt/digikey.csv")
    parser.parse_args()

    cur.execute("""create temporary table tmp (index int, qty int, pn text, mfn text, description text, ref text,
    backorder int, unit_price numeric(5,2), total_price text)""")

    fname = '/home/matt/digikey.csv'
    ebase.csv_remove_quotes(fname)
    with open(fname, 'r') as f:
        if f.read(5) == "Index":
            ebase.csv_remove_header(fname)
            ebase.csv_remove_last_line(fname)

    with open(fname, 'r') as f:
        cur.copy_from(f, 'tmp', sep=',')

    cur.execute("""insert into parts (mfn, description, stock, unit_price) select mfn, description, qty, unit_price
    from tmp on conflict (mfn) do update set stock = parts.stock + (select qty from tmp where tmp.mfn = parts.mfn)""")
    cur.execute("""drop table tmp""")

    c = input("\nCommit? y/n ")
    if c == 'y':
        conn.commit()
    elif c == 'n':
        print("Nothing done.")
        exit(0)
    else:
        print("Must answer y/n.")
        exit(1)

    cur.close()
    conn.close()
