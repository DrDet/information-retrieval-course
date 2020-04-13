#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import codecs
import sys
from typing import Set, Dict
from enum import Enum


class Index:
    def __init__(self, index_file):
        self.inverted_index = {}
        f = open(index_file, "r")
        for line in f:
            doc_id, title, body = line.split("\t")
            doc_id = int(doc_id)
            self._add_to_index(doc_id, title.split())
            self._add_to_index(doc_id, body.split())
        f.close()

    def get_docs(self, word: str) -> Set[int]:
        return self.inverted_index[word] if word in self.inverted_index else set()

    def _add_to_index(self, doc_id, words):
        for w in words:
            postings = self.inverted_index.setdefault(w, set())
            postings.add(doc_id)


# S -> S | M
# S -> M
# M -> M & T
# M -> T
# T -> Term
# T -> (S)

class TreeType(Enum):
    EMPTY = 0
    SUM = 1
    MUL = 2
    TERM = 3


class ExprTree:
    def __init__(self, tree_type: TreeType, val: str = ""):
        self.children = []
        self.tree_type = tree_type
        self.val = val


class QueryParser:
    def __init__(self, query: str):
        self.query = query.strip()
        self.cur = 0
        self.cur_token = ""
        self.is_term = False
        pass

    def _next_cur(self):
        if self.cur == len(self.query):
            self.is_term = False
            self.cur_token = "$"
            return
        if self.query[self.cur].isspace():
            self.is_term = False
            self.cur_token = "&"
            while self.cur < len(self.query) and self.query[self.cur].isspace():
                self.cur += 1
        elif self.query[self.cur].isalnum():
            self.is_term = True
            start = self.cur
            while self.cur < len(self.query) and self.query[self.cur].isalnum():
                self.cur += 1
            self.cur_token = self.query[start:self.cur]
        else:
            self.is_term = False
            self.cur_token = self.query[self.cur]
            self.cur += 1

    def parse(self) -> ExprTree:
        if len(self.query) == 0:
            return ExprTree(TreeType.EMPTY)
        self._next_cur()
        res = self.parse_sum()
        assert self.cur_token == "$"
        return res

    """
    Invariant: Each parse
    1. obtains cur_token at the first acceptable pos
    2. leaves cur_token right after the last acceptable pos
    """

    def parse_sum(self) -> ExprTree:
        flat = True
        res = ExprTree(TreeType.SUM)
        res.children.append(self.parse_mul())
        while True:
            if self.cur_token == "|":
                flat = False
                self._next_cur()
                res.children.append(self.parse_mul())
            else:
                return res if not flat else res.children[0]

    def parse_mul(self) -> ExprTree:
        flat = True
        res = ExprTree(TreeType.MUL)
        res.children.append(self.parse_term())
        while True:
            if self.cur_token == "&":
                flat = False
                self._next_cur()
                res.children.append(self.parse_term())
            else:
                return res if not flat else res.children[0]

    def parse_term(self) -> ExprTree:
        res = None
        if self.is_term:
            res = ExprTree(TreeType.TERM, self.cur_token)
        elif self.cur_token == "(":
            self._next_cur()
            res = self.parse_sum()
            assert self.cur_token == ")"
        else:
            assert False and "Unexpected token: " + self.cur_token
        self._next_cur()
        return res


class QueryHandler:
    def __init__(self, index: Index, qid: int, query_tree: ExprTree):
        self.index = index
        self.qid = qid
        self.query_tree = query_tree

    def search(self) -> Set[int]:
        return self._search_impl(self.query_tree)

    def _search_impl(self, root: ExprTree) -> Set[int]:
        if root.tree_type == TreeType.SUM:
            return set().union(*map(self._search_impl, root.children))
        if root.tree_type == TreeType.MUL:
            return self._search_impl(root.children[0]).intersection(*map(self._search_impl, root.children[1:]))
        if root.tree_type == TreeType.TERM:
            return self.index.get_docs(root.val)
        if root.tree_type == TreeType.EMPTY:
            return set().union(*self.index.inverted_index.values())


class SearchResults:
    def __init__(self):
        self.relevant = {}

    def add(self, qid: int, relevant_docs: Set[int]):
        self.relevant[qid] = relevant_docs

    def print_submission(self, objects_file, submission_file):
        objs = open(objects_file, "r")
        out = open(submission_file, "w")
        out.write("ObjectId,Relevance\n")
        first = True
        for line in objs:
            if first:
                first = False
                continue
            obj_id, q_id, doc_id = map(int, line.split(","))
            relevance = doc_id in self.relevant[q_id]
            out.write("%d,%d\n" % (obj_id, relevance))
        objs.close()
        out.close()


def main():
    # Command line arguments.
    parser = argparse.ArgumentParser(description='Homework 2: Boolean Search')
    parser.add_argument('--queries_file', required=True, help='queries.numerate.txt')
    parser.add_argument('--objects_file', required=True, help='objects.numerate.txt')
    parser.add_argument('--docs_file', required=True, help='docs.tsv')
    parser.add_argument('--submission_file', required=True, help='output file with relevances')
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
            query_handler = QueryHandler(index, qid, QueryParser(query).parse())
            # Search and save results.
            search_results.add(qid, query_handler.search())

    # Generate submission file.
    search_results.print_submission(args.objects_file, args.submission_file)


if __name__ == "__main__":
    main()
