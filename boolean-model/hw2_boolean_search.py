#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import codecs
import sys


class Index:
    def __init__(self, index_file):
        self.inverted_index = {}
        f = open(index_file, "r")
        for line in f:
            doc_id, title, body = line.split("\t")
            self._add_to_index(doc_id, title.split())
            self._add_to_index(doc_id, body.split())
        f.close()

    def _add_to_index(self, doc_id, words):
        for w in words:
            postings = self.inverted_index.setdefault(w, set())
            postings.add(doc_id)


class QueryTree:
    def __init__(self, qid, query):
        # TODO: parse query and create query tree
        pass

    def search(self, index):
        # TODO: lookup query terms in the index and implement boolean search logic
        pass


class SearchResults:
    def add(self, found):
        # TODO: add next query's results
        pass

    def print_submission(self, objects_file, submission_file):
        # TODO: generate submission file
        pass


def main():
    # Command line arguments.
    parser = argparse.ArgumentParser(description='Homework 2: Boolean Search')
    parser.add_argument('--queries_file', required = True, help='queries.numerate.txt')
    parser.add_argument('--objects_file', required = True, help='objects.numerate.txt')
    parser.add_argument('--docs_file', required = True, help='docs.tsv')
    parser.add_argument('--submission_file', required = True, help='output file with relevances')
    args = parser.parse_args()

    # Build index.
    index = Index(args.docs_file)

    # Process queries.
    search_results = SearchResults()
    with codecs.open(args.queries_file, mode='r', encoding='utf-8') as queries_fh:
        for line in queries_fh:
            fields = line.rstrip('\n').split('\t')
            qid = int(fields[0])
            query = fields[1]

            # Parse query.
            query_tree = QueryTree(qid, query)

            # Search and save results.
            search_results.add(query_tree.search(index))

    # Generate submission file.
    search_results.print_submission(args.objects_file, args.submission_file)


if __name__ == "__main__":
    main()

