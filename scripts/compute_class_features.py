from __future__ import print_function

import numpy as np
import re
from classifier.dataset import TaggedDataset
from input.utils import get_class_map
from input.utils import load_mlb
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.feature_selection import mutual_info_classif

# import pandas as pd

stop_tokens = ['_infn_', '_inprot_', '_ingen_', '_inacc_']

UNIPROT_CLASSES = (
    (1, 'Expression'),
    (2, 'Family & Domains'),
    (3, 'Function'),
    (4, 'Interaction'),
    (5, 'Names'),
    (6, 'Pathology & Biotech'),
    (7, 'PTM/processing'),
    (8, 'Sequences'),
    (9, 'Structure'),
    (10, 'Subcellular location'),
    (11, 'Miscellaneous'),
)


def __vectorize_count(X, max_features=5000, tfidf=False, ngram=1, max_df=.95, min_df=10):
    if tfidf:
        _vectorizer = TfidfVectorizer(max_features=max_features, ngram_range=(1, ngram), max_df=.95, min_df=10)
    else:
        _vectorizer = CountVectorizer(max_features=max_features, ngram_range=(1, ngram), max_df=.95, min_df=10)
    X = _vectorizer.fit_transform(X)
    return X, _vectorizer.get_feature_names()


def process_corpus(data_file):
    fids, X, y = [], [], []
    with open(data_file) as f:
        for line in f.readlines():
            line = line.strip()
            try:
                fid, cat, text = line.split(' ', maxsplit=2)
                X.append(text)
                y.append(cat)
                fids.append(fid)
            except Exception as e:
                print(e)
                print(line)
    return fids, X, y


def __process_doc_tag(doc_tag):
    text = ''
    for line in doc_tag:
        if line.startswith('INTRODUCTION'):
            line = line.split()
            line = [t[:20] for t in line if len(t) > 2]
            line = ' '.join(line)
            text += line + ' '
    return text


def process_neg_corpus(source_dir):
    fids, X, y = [], [], []
    alldocs = TaggedDataset(source_dir)
    for doc in alldocs.get_content(merged=False):
        text = __process_doc_tag(doc[1])
        if len(text) > 0:
            fids.append(doc[0])
            X.append(text)
            y.append(1)
        text = __process_doc_tag(doc[2])
        if len(text) > 0:
            fids.append(doc[0])
            X.append(text)
            y.append(0)
    return fids, X, y


def mutual_information(X, y, features, k=200):
    print('fitting on a ' + str(X.shape[0]) + 'x' + str(X.shape[1]) + ' set')
    mi = mutual_info_classif(X, y)
    _feate = []
    _score = []
    for i in np.argsort(-mi)[:k]:
        # print('selected features', features[i], mi[i])
        _feate.append(features[i])
        _score.append(mi[i])
    return _feate, _score


def features_per_class(X, y, fids, cmap):
    categories = set(y)
    for c in categories:
        Xp, Xn, yp, yn = [], [], [], []
        for i in range(len(y)):
            if y[i] == c:
                if sum(cmap[fids[i]]) == 1:
                    Xp.append(X[i].toarray()[0])
                    yp.append(1)
                else:
                    Xn.append(X[i].toarray()[0])
                    yn.append(0)
            # else:
            #     Xn.append(X[i].toarray()[0])
            #     yn.append(0)
        print(c, ' positive:', len(Xp), ' negative:', len(Xn), ' all:', X.shape[0])
        yield c, np.array(Xp + Xn), np.array(yp + yn)


def save_features(features, score, dest_file):
    with open(dest_file, mode='w') as f:
        for i in range(len(features)):
            print(features[i], score[i], file=f)
    f.close()


def __process_cat(cat, X, y, features, k, dest_dir):
    print('extracting info for category : ' + cat)
    _feat, _score = mutual_information(X, y, features, k=k)
    dest_file = dest_dir + '/' + cat + '_terms.csv'
    save_features(_feat, _score, dest_file)


def extract_neg_info_tokens(data_file, dest_dir, max_features=5000, k=200, ngram=1):
    fids, _X, y = process_neg_corpus(data_file)
    X, features = __vectorize_count(_X, max_features=max_features, ngram=ngram)

    cat = 'neg'
    __process_cat(cat, X, y, features, k * 5, dest_dir)


def extract_info_tokens(data_file, dest_dir, cmap, max_features=5000, k=200, ngram=1):
    fids, _X, y = process_corpus(data_file)
    X, features = __vectorize_count(_X, max_features=max_features, ngram=ngram)

    cat = 'all'
    __process_cat(cat, X, y, features, k * 5, dest_dir)
    print()

    for cat, nX, ny in features_per_class(X, y, fids, cmap):
        __process_cat(cat, nX, ny, features, k, dest_dir)
        print()


def extract_text(source_dir, dest_file, cmap):
    mlb = load_mlb()

    alldocs = TaggedDataset(source_dir)
    count = 0
    with open(dest_file, mode='w') as f:
        for doc in alldocs.get_content():
            doc_id = doc[0]
            doc_classes = np.array([cmap[doc_id]])
            class_labels = mlb.inverse_transform(doc_classes)[0]
            for c in class_labels:
                c = re.sub(r'[^\w]', '_', c)
                print(doc_id, c, *(doc[1] + doc[2]), file=f)

            count += 1
            if count % 1000 == 0:
                print(str(count) + ' files processed')
    f.close()


def vectorize(sample, features):
    X = [0] * len(features)
    sample = sample.split()
    for token in sample:
        if token in features:
            X[features[token]['index']] = features[token]['index']
    return X


def annotate_file(samples, pos_features, neg_features, is_positive):
    section, line, y, X = [], [], [], []
    for sample in samples:
        line_section, line_num, line_range, text = sample.split(' ', maxsplit=3)

        Xp = vectorize(text, pos_features)
        Xn = vectorize(text, neg_features)
        # if sum(Xp) > 0:# and sum(Xn) > 0:
        section.append(line_section)
        line.append(line_num)
        if is_positive and sum(Xp) > sum(Xn):
            y.append(1)
            X.append(Xp + Xn)
            # elif not is_positive and sum(Xp) < sum(Xn):
            # else:
            #    y.append(0)
            #    X.append(Xp + Xn)
    return section, line, y, X


def get_class_name_map(mlb):
    cnmap = {}
    for c in mlb.classes_:
        cid = re.sub(r'[^\w]', '_', c)
        cnmap[c] = cid
    return cnmap


def get_features(feature_dir, class_names, k=200):
    res = {}
    for c in class_names.keys():
        res[c] = {}
        feat_score = {}
        cid = class_names[c]
        with open(feature_dir + '/' + cid + '_terms.csv') as f:
            count = 0
            for line in f.readlines()[:k]:
                feat, score = line.strip().split()
                feat_score[feat] = {'score': float(score), 'index': count}
                count += 1
        res[c] = feat_score
    return res


def get_neg_features(features, upclass, feature_dir, k=200):
    # fP = features[upclass]
    cat = 'neg'
    fN = {}
    with open(feature_dir + '/' + cat + '_terms.csv') as f:
        for line in f.readlines()[:k]:
            feat, score = line.strip().split()
            fN[feat] = {'score': float(score)}

    for c in features.keys():
        if c != upclass:
            for feat in features[c].keys():
                if feat not in fN:
                    fN[feat] = features[c][feat]['score']
                else:
                    fN[feat] += features[c][feat]['score']
    feat_score = {}
    count = 0
    for token in sorted(fN, key=fN.get, reverse=True)[:k]:
        if token not in stop_tokens:
            feat_score[token] = {'score': fN[token], 'index': count}
            count += 1

    return feat_score


def extract_evidence(source_dir, feature_dir, dest_file, cmap, k=200):
    mlb = load_mlb()
    cnmap = get_class_name_map(mlb)

    features = get_features(feature_dir, cnmap, k=k)
    neg_features = {i: get_neg_features(features, i, k=k) for i in features.keys()}

    # feat_set = set()
    # for feat_score in features.values():
    #     for token in feat_score[0]:
    #         feat_set.add(token)

    alldocs = TaggedDataset(source_dir)
    count = 0
    with open(dest_file, mode='w') as f:
        for doc in alldocs.get_content(merged=False):
            doc_id = doc[0]
            doc_classes = np.array([cmap[doc_id]])
            class_labels = mlb.inverse_transform(doc_classes)[0]
            for c in class_labels:
                sectionp, linep, yp, Xp = annotate_file(doc[1], features[c], neg_features[c], True)
                sectionn, linen, yn, Xn = annotate_file(doc[2], features[c], neg_features[c], True)
                # [print(doc_id, cnmap[c], sectionp[i], linep[i], 1, yp[i], *Xp[i], file=f) for i in range(len(yp))]
                [print(doc_id, cnmap[c], sectionp[i], linep[i], 1, yp[i], file=f) for i in range(len(yp))]
                # [print(doc_id, cnmap[c], sectionn[i], linen[i], 1, yn[i], *Xn[i], file=f) for i in range(len(yn))]
                [print(doc_id, cnmap[c], sectionn[i], linen[i], 0, yn[i], file=f) for i in range(len(yn))]
            count += 1
            if count % 100 == 0:
                print(str(count) + ' files processed')
    f.close()


if __name__ == '__main__':
    # create_corpus = True
    create_corpus = False
    info_tokens = True
    evidence = False
    ngram = 1
    source_dir = '/data/user/teodoro/uniprot/dataset/no_large/train/tag/'
    # source_dir = '/data/user/teodoro/uniprot/dataset/no_large/test/tag'
    feat_dir = '/data/user/teodoro/uniprot/dataset/no_large/features/'
    evi_file = '/data/user/teodoro/uniprot/dataset/no_large/evidence/data.txt'

    max_features = 10000
    k = 500

    cmap = get_class_map()

    if create_corpus:
        print('extracting text data')
        extract_text(source_dir, dest_file=feat_dir + 'data.txt', cmap=cmap)

    if info_tokens:
        print('extracting informative tokens')
        extract_info_tokens(feat_dir + 'data.txt', feat_dir, cmap, max_features=max_features, k=k, ngram=ngram)
        extract_neg_info_tokens(source_dir, feat_dir, max_features=max_features, k=k, ngram=ngram)

    k = 200
    if evidence:
        print('extracting evidence')
        extract_evidence(source_dir, feat_dir, evi_file, cmap, k=k)
