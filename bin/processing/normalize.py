import logging
import os
import re
import string

import nltk
from nltk.stem.porter import PorterStemmer
from sklearn.externals import joblib

from . import pos_classifier as pc
from . import spelling as sp


# TODO run with stopwords without stopwords, save all inputs
def process_tweets(df_tweets, colname='tweet', reprocess=False):
    """
    Processes, stems, parses, and normalizes tweet text, including separating emojis and hashtags
    :param df_tweets: pandas DataFrame
    :param colname: String name of column containing tweet
    :param reprocess: Boolean to redo processing steps if postprocessed frame does not exist
    :return: Inputted pandas DataFrame with column processed
    """
    logging.debug('Entering process_tweets()')
    if not os.path.isfile('../data/postprocessed.pkl') or reprocess:
        if reprocess:
            logging.debug('process_tweets(): Reprocess flag set to TRUE, beginning processing.')
        # Cleaning
        df_tweets[colname] = df_tweets[colname].apply(case_correction)
        df_tweets[colname] = df_tweets[colname].apply(remove_mentions)
        df_tweets[colname] = df_tweets[colname].apply(remove_retweets)
        df_tweets['emoji'] = df_tweets[colname].apply(emoji_extraction)
        df_tweets[colname] = df_tweets[colname].apply(emoji_removal)
        df_tweets['hashtag'] = df_tweets[colname].apply(hashtag_extraction)
        df_tweets[colname] = df_tweets[colname].apply(hashtag_removal)
        df_tweets[colname] = df_tweets[colname].apply(clean_special_characters)
        # Tokenizing
        df_tweets[colname] = df_tweets[colname].apply(tokenize)
        logging.debug('process_tweets(): Checkpoint 1')
        joblib.dump(df_tweets, '../data/normalize-checkpoints/point1.pkl')

        # region Spelling workflow
        logging.debug('process_tweets(): Entering spelling workflow')
        dict_location = '../data/wordlist.pkl'
        if os.path.isfile(dict_location):
            word_dict = sp.load_dictionary(dict_location)
        else:
            sp.generate_dictionary(dict_location)
            word_dict = sp.load_dictionary(dict_location)

        df_tweets[colname] = df_tweets[colname].apply(sp.spelling_normalization, args=(word_dict, ))
        df_tweets[colname] = df_tweets[colname].apply(sp.remove_repeated_characters)
        # endregion

        logging.debug('process_tweets(): Checkpoint 2')
        joblib.dump(df_tweets, '../data/normalize-checkpoints/point2.pkl')

        classifier = pc.get_classifier()
        logging.debug('process_tweets(): Tagging POS.')
        df_tweets['pos'] = df_tweets[colname].apply(pc.tag, args=(classifier, ))

        logging.debug('process_tweets(): Checkpoint 3')
        joblib.dump(df_tweets, '../data/normalize-checkpoints/point3.pkl')

        df_tweets[colname] = df_tweets[colname].apply(porter_stemming)

        # TODO with and without stopwords?
        df_tweets['bigram'] = df_tweets[colname].apply(bigram_creation)
        df_tweets['trigram'] = df_tweets[colname].apply(trigram_creation)
        df_tweets['bigram_pos'] = df_tweets['pos'].apply(bigram_creation)
        df_tweets['trigram_pos'] = df_tweets['pos'].apply(trigram_creation)
        df_tweets['rejoin'] = df_tweets[colname].apply(rejoin)

        # Stopword
        df_tweets['stopped'] = df_tweets[colname].apply(stopword_removal)
        df_tweets['rejoin2'] = df_tweets['stopped'].apply(rejoin)

        logging.debug("process_tweets(): Dumping processed dataframe into '../data/postprocessed.pkl'")
        joblib.dump(df_tweets, '../data/postprocessed.pkl')
    else:
        logging.debug("process_tweets(): Bypassing processing step, loading 'postprocessed.pkl'.")
        df_tweets = joblib.load('../data/postprocessed.pkl')
    return df_tweets


# region Helper Functions
# region Pre-tokenizing Workflow
def remove_mentions(element):
    """Remove twitter mentions '@name' from text"""
    return re.sub(r'@[a-zA-Z_0-9]{1,15}', '', element)


def remove_retweets(element):
    """Removes 'RT:', representing retweets"""
    return re.sub(r'RT ?:?', '', element, flags=re.IGNORECASE)


# region Feature extraction and removal
def emoji_extraction(text):
    """Returns unicode emojis"""
    return re.findall(r'&#\d+;?', text)


def emoji_removal(text):
    """Removes unicode emojis from string"""
    return re.sub(r'&#\d+;?', '', text)


def hashtag_extraction(text):
    """Returns twitter hashtags"""
    return re.findall(r'#\w+', text)


def hashtag_removal(text):
    """Removes twitter hashtags from string"""
    return re.sub(r'#\w+', '', text)
# endregion


def clean_special_characters(text):
    """Substitutes 'and' for ampersands, removes hyperlinks and punctuation"""
    text = re.sub(r'&amp', 'and', text)
    text = re.sub(r'http[a-zA-Z0-9:/.-]+', '', text)  # Remove hyperlinks
    # Remove punctuation
    punct = re.compile('[{}]'.format(re.escape(string.punctuation)))
    text = re.sub(punct, '', text)
    return text
# endregion


# region Tokenizing, n-gram Creation
def tokenize(corpus):  # or just word tokenizing
    """Tokenizes / creates unigrams from text"""
    return nltk.WhitespaceTokenizer().tokenize(corpus)


def bigram_creation(corpus):
    """Creates list of bigrams from text"""
    grams = list(zip(corpus, corpus[1:]))
    out = []
    for gram in grams:
        out.append('-'.join(gram))
    return out


def trigram_creation(corpus):
    """Creates list of trigrams from text"""
    grams = list(zip(corpus, corpus[1:], corpus[2:]))
    out = []
    for gram in grams:
        out.append('-'.join(gram))
    return out
# endregion


# region Post-tokenizing Workflow
def case_correction(text):
    """Returns lowercase string"""
    return text.lower()


def stopword_removal(text):
    """Removes stopwords from list of words as determined by nltk"""
    stopwords = nltk.corpus.stopwords.words('english')
    return [word for word in text if word not in stopwords]


def porter_stemming(text):
    """Applies Porter stemming algorithm"""
    pstem = PorterStemmer()
    return [pstem.stem(word) for word in text]


def rejoin(text):
    """Rejoins tokenized items"""
    return ' '.join(text)

# endregion
# endregion


def make_binary(text, class_to_change, class_changed_to):
    """Convert 3 class-classification to binary problem"""
    if text == class_to_change:
        return class_changed_to
    else:
        return text
