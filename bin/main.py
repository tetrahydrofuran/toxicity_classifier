import logging
import os

import pandas as pd

import processing.normalize
from processing import pos_classifier as pc

logging.getLogger().setLevel(logging.DEBUG)

# region CONFIG SETTINGS
POS_CLASSIFIER = True  # True for Naive Bayes Classifier, False for Tree
# endregion


def main():
    tweets = pd.read_csv('../data/data.csv', index_col=0)
    processing.normalize.process_tweets(tweets)


def main2():
    if POS_CLASSIFIER:
        if not os.path.isfile('../data/pos_bayes_classifier.pkl'):
            pc.export_pos_classifier(classifier='bayes', state=42)
        clf = pc.load_pos_classifier('bayes')
    else:
        if not os.path.isfile('../data/pos_tree_classifier.pkl'):
            clf = pc.export_pos_classifier(classifier='tree', state=42)
        clf = pc.load_pos_classifier('tree')
    pass

if __name__ == "__main__":
    main()
