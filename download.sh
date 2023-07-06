#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 <destination_path> <requirements_file_path>" >&2
    exit 1
fi

destination_path=$(realpath $1)
requirements_file_path=$(realpath $2)

source env/bin/activate
while IFS= read -r line; do
    pip download $line --no-deps --no-binary :all: --dest $destination_path
done < $requirements_file_path
deactivate