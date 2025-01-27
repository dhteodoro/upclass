import os
import numpy as np
from gensim.models.doc2vec import Doc2Vec

from classifier.dataset import TaggedDataset, SentenceDataset
from input.regressors import get_labelled_set, get_feature_set, get_label_set, get_file_id
from input.utils import get_class_map

SOURCE_DATA_DIR = '/data/user/teodoro/uniprot/dataset/pub_data/'
SOURCE_MODEL_DIR = '/data/user/teodoro/uniprot/model/pub_model/'


def get_dev_test_pmids():
    colls = ['dev', 'test']
    dev_pmids, test_pmids = [], []
    for coll in colls:
        source_dir = SOURCE_DATA_DIR + coll + '/sentence'
        for dirname, dirnames, filenames in os.walk(source_dir):
            for filename in filenames:
                if filename.endswith('.txt'):
                    if coll == 'dev':
                        dev_pmids.append(filename.replace('.txt', ''))
                    elif coll == 'test':
                        test_pmids.append(filename.replace('.txt', ''))
                    else:
                        print('this should not be here')
                        break
    return dev_pmids, test_pmids


def get_test_labelled_set(models, source_dir, cmap, mtype='both', in_set=None, n_jobs=20):
    tag_doc, no_tag_doc = (None, None)
    if 'tag_dbow' in models or 'tag_dmc' in models:
        tag_doc = {}
        source_tag = source_dir + '/tag'
        tds = TaggedDataset(source_tag)
        for doc in tds:
            doc_id = get_file_id(doc.tags[0])
            if in_set is None or len(in_set) == 0 or doc_id in in_set:
                tag_doc[doc.tags[0]] = doc.words
    if 'notag_dbow' in models or 'notag_dmc' in models:
        source_no_tag = source_dir + '/sentence'
        sds = SentenceDataset(source_no_tag)
        no_tag_doc = {}
        for doc in sds:
            doc_id = get_file_id(doc.tags[0])
            if in_set is None or len(in_set) == 0 or doc_id in in_set:
                no_tag_doc[doc.tags[0]] = doc.words
    doc_tags = None
    if tag_doc is not None:
        doc_tags = tag_doc.keys()
    else:
        doc_tags = no_tag_doc.keys()

    p_doc_tags, label_list = get_label_set(doc_tags, in_set, [], cmap)

    p_doc_tags, feature_list = get_feature_set(models, doc_tags, [], [], text_tag=tag_doc, text_notag=no_tag_doc,
                                               mtype=mtype, n_jobs=n_jobs)

    return p_doc_tags, feature_list, label_list


dev_pmids, test_pmids = get_dev_test_pmids()
cmap = get_class_map()

models_tag = SOURCE_MODEL_DIR+'tag'
models_notag = SOURCE_MODEL_DIR+'no_tag'
models = {
    'tag_dbow': Doc2Vec.load(models_tag + '/dbow'),
    #'tag_dmc': Doc2Vec.load(models_tag + '/dmc')  # ,
    'notag_dbow': Doc2Vec.load(models_notag + '/dbow'),
    'notag_dmc': Doc2Vec.load(models_notag + '/dmc')
}

mtype = None
dest_dir = None
if len(models) == 4:
    mtype = 'both'
    dest_dir = 'both'
elif len(models) == 2:
    mtype = 'tag'
    dest_dir = 'tag'
elif len(models) == 3:
    mtype = 'notag'
    dest_dir = 'no_tag'
else:
    print('unknown model length')
    exit()

# train_docs, train_features, train_labels = get_labelled_set(models, [], set(dev_pmids + test_pmids), cmap, mtype=mtype)
#
# print('size train', len(train_features))
# print('shape train', len(train_features[0]))
# print('size train labels', len(train_labels))
# print('shape train labels', len(train_labels[0]))
#
# with open(SOURCE_DATA_DIR+'processed/' + dest_dir + '/train_docs.csv', mode='w') as f:
#     for i in train_docs:
#         print(i, file=f)
# f.close()
# fa = np.asarray(train_features)
# np.save(SOURCE_DATA_DIR+'processed/' + dest_dir + '/train_features.npy', fa)
# fl = np.asarray(train_labels)
# np.savetxt(SOURCE_DATA_DIR+'processed/' + dest_dir + '/train_labels.csv', fl, delimiter=',',
#            fmt='%i')

source_dir = SOURCE_DATA_DIR+'dev'
dev_docs, dev_features, dev_labels = get_test_labelled_set(models, source_dir, cmap, mtype=mtype, in_set=set(dev_pmids), n_jobs=20)

print('size dev', len(dev_features))
print('shape dev', len(dev_features[0]))
print('size dev labels', len(dev_labels))
print('shape dev labels', len(dev_labels[0]))

with open(SOURCE_DATA_DIR+'processed/' + dest_dir + '/dev_docs.csv', mode='w') as f:
    for i in dev_docs:
        print(i, file=f)
f.close()
fa = np.asarray(dev_features)
np.savetxt(SOURCE_DATA_DIR+'processed/' + dest_dir + '/dev_features.csv', fa, delimiter=',',
           fmt='%.5f')
fl = np.asarray(dev_labels)
np.savetxt(SOURCE_DATA_DIR+'processed/' + dest_dir + '/dev_labels.csv', fl, delimiter=',',
           fmt='%i')

source_dir = SOURCE_DATA_DIR+'test'
test_docs, test_features, test_labels = get_test_labelled_set(models, source_dir, cmap, mtype=mtype,
                                                              in_set=set(test_pmids), n_jobs=20)

print('size test', len(test_features))
print('shape test', len(test_features[0]))
print('size test labels', len(test_labels))
print('shape test labels', len(test_labels[0]))

with open(SOURCE_DATA_DIR+'processed/' + dest_dir + '/test_docs.csv', mode='w') as f:
    for i in test_docs:
        print(i, file=f)
f.close()
fa = np.asarray(test_features)
np.savetxt(SOURCE_DATA_DIR+'processed/' + dest_dir + '/test_features.csv', fa,
           delimiter=',',
           fmt='%.5f')
fl = np.asarray(test_labels)
np.savetxt(SOURCE_DATA_DIR+'processed/' + dest_dir + '/test_labels.csv', fl, delimiter=',',
           fmt='%i')
