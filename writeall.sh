#!/bin/bash
#
yourfile="$@"
your_script="./write.sh"


# Skip header? Uncomment if needed
tail -n +2 "$yourfile" | while IFS=$'\t' read -r col1 _ col3 _; do
  #col3="${col3%\"}"  # Remove trailing quote
  #col3="${col3#\"}"  # Remove leading quote
  echo "$your_script" "$col1" "$col3"
  "$your_script" "$col1" "$col3"
done
