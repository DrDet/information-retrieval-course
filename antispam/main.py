import argparse
from base64 import b64decode

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier


class Document:
    def __init__(self, id=0, url='', html='', mark=False):
        self.id = id
        self.url = url
        self.html = html
        self.mark = mark


def read_dataset(dataset_file):
    print(dataset_file)
    dataset = []
    with open(dataset_file, "r", encoding="utf-8") as input_file:
        headers = input_file.readline()
        for i, line in enumerate(input_file):
            if i % 1000 == 0:
                print("processed document %d\n" % i)
            parts = line.strip().split('\t')
            url_id = int(parts[0])
            mark = bool(int(parts[1]))
            url = parts[2]
            pageInb64 = parts[3]

            dataset.append(
                Document(id=url_id, url=url, html=b64decode(pageInb64).decode("utf-8", errors="replace"),
                         mark=mark))
    return dataset


def fit_vectorizer(vectorizer, dataset):
    print("... fit vectorizer ...")
    corpus = [doc.html for doc in dataset]
    vectorizer.fit(corpus)
    return corpus


def get_vectorized_dataset(vectorizer, dataset, corpus):
    print("... vectorizing ...")
    y = [doc.mark for doc in dataset]
    X = vectorizer.transform(corpus)
    return X, y


def main():
    parser = argparse.ArgumentParser(description='Homework 3: Antispam')
    parser.add_argument('--train_set', required=True, help='kaggle_train_data_tab.csv')
    parser.add_argument('--test_set', required=True, help='kaggle_test_data_tab.csv')
    parser.add_argument('--submission_file', required=True, help='submission.txt')
    args = parser.parse_args()

    train = read_dataset(args.train_set)
    test = read_dataset(args.test_set)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    train_corpus = fit_vectorizer(vectorizer, train)
    test_corpus = fit_vectorizer(vectorizer, test)

    X_train, y_train = get_vectorized_dataset(vectorizer, train, train_corpus)
    X_test, y_test = get_vectorized_dataset(vectorizer, test, test_corpus)

    clf = SGDClassifier(verbose=True, epsilon=1e-5, class_weight='balanced', penalty='elasticnet')
    print("... fitting model ...")
    clf.fit(X_train, y_train)
    print("... predicting ...")
    y_predicted = clf.predict(X_test)

    print("... writing answer ...")
    with open(args.submission_file, "w") as output_file:
        output_file.write("Id,Prediction\n")
        for doc, mark in zip(test, y_predicted):
            output_file.write("%d,%d\n" % (doc.id, mark))


if __name__ == '__main__':
    main()
