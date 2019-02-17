#!/bin/bash

timestamp() {
    date +"%F-%H.%M.%S"
}

mkdir -p ~/.ebase/backups
cd ~/.ebase/backups
max_files=30
num_files=$(ls -1 | wc -l)
excess_files=$(expr $num_files - $max_files + 1)

while [ $num_files -ge $max_files ]
do
    rm "$(ls | head -1)"
    num_files=$(ls -1 | wc -l)
done

pg_dump electronics_inventory > $(timestamp).sql
