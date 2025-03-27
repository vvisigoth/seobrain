#!/bin/bash

TITLE=$1
KEYWORDS=$2

cd composer

IFS=',' read -ra parts <<< "$KEYWORDS"

for part in "${parts[@]}"; do
  python3.12 ./search_tool.py -o ../research -s $part
done

cd ..

echo "${parts[@]}"

python3.12 ./articlegenerator.py --single --title "$TITLE" --keywords "${parts[@]}" --knowledge research

exit 0
