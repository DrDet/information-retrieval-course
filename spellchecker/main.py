import argparse
import sys
from enum import Enum
from typing import Dict, Tuple

from pandas import read_csv, DataFrame
from Levenshtein import editops
import csv
from collections import namedtuple


class OpType(Enum):
    REPLACE = 0
    INSERT = 1
    DELETE = 2


EditOpClass = namedtuple("EditOp", ["old_char", "new_char", "preceding_ctx", "type"])


def EditOp(old_char, new_char, preceding_ctx=""):
    preceding_ctx: str = preceding_ctx
    old_char: str = old_char
    new_char: str = new_char
    if len(old_char) == len(new_char) == 1:
        op_type = OpType.REPLACE
    elif len(old_char) == 0:
        op_type = OpType.INSERT
    elif len(new_char) == 0:
        op_type = OpType.DELETE
    else:
        assert False
    return EditOpClass(old_char, new_char, preceding_ctx, op_type)


class ErrorModel:
    def __init__(self, Z: float, F: float, S: float):
        assert Z + F + S == 1
        self.Z = Z
        self.F = F
        self.S = S
        self.zero_level: Dict[OpType, int] = {}
        self.first_level: Dict[EditOp, int] = {}
        self.second_level: Dict[EditOp, int] = {}

    def get_weight_of_error(self, old_char: str, new_char: str, preceding_ctx: str) -> float:
        op = EditOp(old_char, new_char, preceding_ctx)
        w_zero = self.zero_level[op.type] if op in self.zero_level else 0
        w_first = self.first_level[op] if op in self.first_level else 0
        w_second = self.second_level[op] if op in self.second_level else 0
        return self.Z * w_zero + self.F * w_first + self.S * w_second

    def add_spelling_correction(self, old_w: str, new_w: str):
        ops = editops(old_w, new_w)
        non_eqs = set()
        for op_type_str, old_i, new_i in ops:
            if op_type_str == 'replace':
                old_char, new_char, op_type = old_w[old_i], new_w[new_i], OpType.REPLACE
            elif op_type_str == 'insert':
                old_char, new_char, op_type = "", new_w[new_i], OpType.INSERT
            else:
                assert op_type_str == 'delete'
                old_char, new_char, op_type = old_w[old_i], "", OpType.DELETE
            non_eqs.add(old_i)
            self._update_models(op_type, old_char, new_char, "" if old_i == 0 else old_w[old_i - 1])
        for old_i in set(range(len(old_w))).difference(non_eqs):
            char = old_w[old_i]
            self._update_models(OpType.REPLACE, char, char, "" if old_i == 0 else old_w[old_i - 1])

    def _update_models(self, op_type, old_char, new_char, preceding_ctx):
        op0 = op_type
        op1 = EditOp(old_char, new_char)
        op2 = EditOp(old_char, new_char, preceding_ctx)
        self.zero_level.setdefault(op0, 0)
        self.first_level.setdefault(op1, 0)
        self.second_level.setdefault(op2, 0)
        self.zero_level[op0] += 1
        self.first_level[op1] += 1
        self.second_level[op2] += 1


class Trie:
    END_MARKER = "$"

    def __init__(self, is_terminal=False, word="", freq=0):
        self.is_terminal = is_terminal
        self.word = word
        self.freq = freq
        self.children: Dict[str, Trie] = {}
        self.vocabulary: Dict[str, int] = {}

    def add_word(self, w: str, freq: int, pos=0):
        if pos == 0:
            self.vocabulary[w] = freq
        if pos == len(w):
            self.children[Trie.END_MARKER] = Trie(True, w, freq)
            return
        char_to_go = w[pos]
        to = self.children.setdefault(char_to_go, Trie())
        to.add_word(w, freq, pos + 1)


class SpellChecker:
    def __init__(self, trie: Trie, error_model: ErrorModel, *,
                 corrections_limit=1,
                 max_nodes_to_go=5,
                 weight_threshold_to_go=0.0,
                 ignore_suffix_len=3):
        self.trie_root: Trie = trie
        self.error_model: ErrorModel = error_model
        self.corrections_limit = corrections_limit
        self.max_nodes_to_go = max_nodes_to_go
        self.weight_threshold_to_go = weight_threshold_to_go
        self.ignore_suffix_len = ignore_suffix_len

    def correct_spelling(self, word: str):
        corrections = self._get_corrections(self.trie_root, word)
        corrections.sort(key=lambda x: x[1], reverse=True)
        if len(corrections) == 0:
            return word
        best, best_freq = corrections[0]
        if word in self.trie_root.vocabulary and best_freq < 5 * self.trie_root.vocabulary[word]:
            return word
        return best

    def _get_corrections(self, node: Trie, word: str, pos=0, done_corrections=0) -> [Tuple[str, int]]:
        if pos == len(word):
            if Trie.END_MARKER in node.children:
                terminal_node = node.children[Trie.END_MARKER]
                return [(terminal_node.word, terminal_node.freq)]
            else:
                return []
        letters_to_go = []
        max_weight = 0
        for next_trie_letter, child in node.children.items():
            if next_trie_letter == Trie.END_MARKER:
                continue
            weight = self.error_model.get_weight_of_error(word[pos], next_trie_letter, word[pos - 1] if pos > 0 else "")
            max_weight = max(max_weight, weight)
            letters_to_go.append((next_trie_letter, weight))
        if len(letters_to_go) == 0:
            return []
        letters_to_go.sort(key=lambda x: x[1], reverse=True)
        letters_to_go = list(filter(lambda x: x[1] >= self.weight_threshold_to_go * max_weight,
                                    letters_to_go[:self.max_nodes_to_go]))
        res = []
        for letter, _ in letters_to_go:
            is_correction = letter != word[pos]
            if is_correction and pos >= len(word) - self.ignore_suffix_len:
                continue
            new_corrections_cnt = done_corrections + is_correction
            if new_corrections_cnt <= self.corrections_limit:
                node_to_go = node.children[letter]
                res += self._get_corrections(node_to_go, word, pos + 1, new_corrections_cnt)
        return res


def main():
    parser = argparse.ArgumentParser(description='Homework 2: Spellchecker')
    parser.add_argument('--words', required=True, help='Vocabulary words with frequencies (csv: Id,Freq)')
    parser.add_argument('--train', required=True, help='Spelling_corrections (csv: Id,Expected)')
    parser.add_argument('--test', required=True, help='csv: Id,Predicted')
    parser.add_argument('--submission', required=True, help='csv: Id,Predicted')
    args = parser.parse_args()

    MAX_WORD_LEN = 950

    words = read_csv(args.words, converters={'Id': str})
    trie_root = Trie()
    for index, row in words.iterrows():
        if index % 50000 == 0:
            print("... building language model %d ..." % index)
        word = row['Id']
        if len(word) > MAX_WORD_LEN:
            print("skip word at index %d: length = %d -- too big" % (index, len(word)))
            continue
        trie_root.add_word(word, int(row['Freq']))

    train = read_csv(args.train, converters={'Id': str, 'Expected': str})
    error_model = ErrorModel(0, 0.4, 0.6)
    for index, row in train.iterrows():
        if index % 50000 == 0:
            print("... training error model %d ..." % index)
        error_model.add_spelling_correction(row['Id'], row['Expected'])

    test = read_csv(args.test, converters={'Id': str})
    spell_checker = SpellChecker(trie_root, error_model, weight_threshold_to_go=0.1)
    with open(args.submission, 'w') as out:
        writer = csv.writer(out, delimiter=',')
        writer.writerow(['Id', 'Predicted'])
        corrections_cnt = 0
        for index, row in test.iterrows():
            if index % 50000 == 0:
                print("... testing %d, corrections_cnt: %d ..." % (index, corrections_cnt))
            word = row['Id']
            if len(word) > MAX_WORD_LEN:
                print("skip word at index %d: length = %d -- too big" % (index, len(word)))
                correction = word
            else:
                correction = spell_checker.correct_spelling(word)
            if word != correction:
                if corrections_cnt % 10 == 0:
                    print("%s -> %s" % (word, correction))
                corrections_cnt += 1
            writer.writerow([word, correction])
        print("done, total corrections: %d" % corrections_cnt)


if __name__ == '__main__':
    main()
