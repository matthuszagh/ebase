# ebase
Electronic parts inventory management.

#### Description
Ebase consists of a set of Python scripts to create and manage an electronic parts database in
Postgres. It integrates well with KiCad and Digi-Key, and provides significant automation for adding
parts to the database, removing parts when a project is built, determining additional parts needed
to build a project and uploading the requisite parts to Digi-Key for ordering.

#### Prerequisites
[psycopg](http://initd.org/psycopg/)
[Postgres](https://www.postgresql.org/)
