timeout -s $1 -t 10000 python3 hw2_boolean_search.py --queries_file=data/queries.numerate.txt --docs_file=data/docs.tsv --objects_file=data/objects.numerate.txt --submission_file=data/submission.txt
echo "Diff size lines:"
diff data/submission.txt data/right | wc -l