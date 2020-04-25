import argparse
from enum import Enum
from typing import Dict, Tuple

from pandas import read_csv
from Levenshtein import editops


class OpType(Enum):
    REPLACE = 0
    INSERT = 1
    DELETE = 2


class EditOp:
    def __init__(self, old_char, new_char, preceding_ctx=""):
        self.preceding_ctx: str = preceding_ctx
        self.old_char: str = old_char
        self.new_char: str = new_char
        if len(old_char) == len(new_char) == 1:
            self.type = OpType.REPLACE
        elif len(old_char) == 0:
            self.type = OpType.INSERT
        elif len(new_char) == 0:
            self.type = OpType.DELETE


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
        cnt0 = self.zero_level.setdefault(op_type, 0)
        cnt1 = self.first_level.setdefault(EditOp(old_char, new_char), 0)
        cnt2 = self.second_level.setdefault(EditOp(old_char, new_char, preceding_ctx), 0)
        cnt0 += 1
        cnt1 += 1
        cnt2 += 1


def main():
    parser = argparse.ArgumentParser(description='Homework 2: Spellchecker')
    parser.add_argument('--words', required=True, help='Vocabulary words with frequencies (csv: Id,Freq)')
    parser.add_argument('--train', required=True, help='Spelling_corrections (csv: Id,Expected)')
    parser.add_argument('--test', required=True, help='csv: Id,Predicted')
    parser.add_argument('--submission', required=True, help='csv: Id,Predicted')
    args = parser.parse_args()

    words = read_csv(args.words)
    train = read_csv(args.train)

    error_model = ErrorModel(0.1, 0.3, 0.6)
    for index, row in train.iterrows():
        if index % 50000 == 0:
            print("... training %d ..." % index)
        error_model.add_spelling_correction(row['Id'], row['Expected'])

    # print(words.sort_values("Freq", ascending=False).head(20))
    print(editops("фперзидеед", "пт"))


if __name__ == '__main__':
    main()

# из исправлений использовать только replace'ы (insert, delete не надо)
# не больше одного исправления в слове
# не менять окончания слов (последние 3 буквы)
# исправлять только слова с русскими буквами (70% слов) ?
# исправлять только если исправление СИЛЬНО вероятнее чем запрос пользователя (в 5 раз)
