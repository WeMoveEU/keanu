#!/bin/bash

EXIT_CODE=0
FILES="erd/keanu-schema.sql sql/views.sql sql/campaign.sql sql/action.sql sql/contact.sql sql/contact_action.sql"

if [ -n "$1" ]
then
  FILES=$1
fi 

for f in $FILES
do
  echo "$(date +'%F %T'): Starting execution of $f..."
  mysql keanu < $f
  code=$?
  echo "$(date +'%F %T'): Execution of $f done."
  EXIT_CODE=$[$EXIT_CODE+$code]
done

exit $EXIT_CODE
