#!/usr/bin/python

# 3rd party modules
import psycopg2
# internal
import ebase

if __name__ == '__main__':
    conn = ebase.db_conn()
    cur = conn.cursor()

    cur.execute(
        """select * from parts where stock > 0 and (storage = '') is not false group by mfn""")
    print(cur.fetchall())

    cur.close()
    conn.close()
