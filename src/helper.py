import pathlib
import numpy as np
from nltk.tokenize import word_tokenize


def checkFile(filename):
    return pathlib.Path(filename).is_file()


def invertDic(my_map, struct='o2o'):
    inv_map = {}

    if struct == 'o2o':  # Reversing one-to-one dictionary
        for k, v in my_map.items():
            inv_map[v] = k

    elif struct == 'm2o':  # Reversing many-to-one dictionary
        for k, v in my_map.items():
            inv_map[v] = inv_map.get(v, [])
            inv_map[v].append(k)

    elif struct == 'm2ol':  # Reversing many-to-one list dictionary
        for k, v in my_map.items():
            for ele in v:
                inv_map[ele] = inv_map.get(ele, [])
                inv_map[ele].append(k)

    elif struct == 'm2os':
        for k, v in my_map.items():
            for ele in v:
                inv_map[ele] = inv_map.get(ele, set())
                inv_map[ele].add(k)

    elif struct == 'ml2o':  # Reversing many_list-to-one dictionary
        for k, v in my_map.items():
            for ele in v:
                inv_map[ele] = inv_map.get(ele, [])
                inv_map[ele] = k

    elif struct == 'l2s':
        for k in my_map.keys():
            inv_map[k] = set(my_map[k])
    return inv_map


# Get embedding of words from gensim word2vec model
def getEmbeddings(model, phr_list, embed_dims, mode='crawl'):
    embed_list = []
    all_num, oov_num, oov_rate = 0, 0, 0
    for phr in phr_list:
        # phr = phr.lower()
        if mode == 'crawl' and (phr in model.vocab or phr.lower().replace(' ', '_') in model.vocab):
            if phr in model.vocab:
                embed_list.append(model.word_vec(phr))
            elif phr.lower().replace(' ', '_') in model.vocab:
                embed_list.append(model.word_vec(phr.lower().replace(' ', '_')))
            all_num += 1
        elif mode == 'kg2vec_ALOD' and (phr in model.vocab or phr.lower().replace(' ', '_') in model.vocab):
            all_num += 1
            if phr in model.vocab:
                embed_list.append(model.vectors[model.vocab[phr].index])
            elif phr.lower().replace(' ', '_') in model.vocab:
                embed_list.append(model.vectors[model.vocab[phr.lower().replace(' ', '_')].index])
        elif mode == 'kg2vec_dbnary' and ('http://kaiko.getalp.org/dbnary/eng/' + phr.replace(' ', '_') in model.vocab):
            all_num += 1
            embed_list.append(
                model.vectors[model.vocab['http://kaiko.getalp.org/dbnary/eng/' + phr.replace(' ', '_')].index])
        elif mode == 'kg2vec_dbpedia' and ('http://dbpedia.org/ontology/' + phr.replace(' ', '_') in model.vocab or
                                           'http://dbpedia.org/resource/' + phr.replace(' ', '_') in model.vocab):
            all_num += 1
            if 'http://dbpedia.org/ontology/' + phr.replace(' ', '_') in model.vocab:
                embed_list.append(model.wv.get_vector('http://dbpedia.org/ontology/' + phr.replace(' ', '_')))
            elif 'http://dbpedia.org/resource/' + phr.replace(' ', '_') in model.vocab:
                embed_list.append(model.wv.get_vector('http://dbpedia.org/resource/' + phr.replace(' ', '_')))
        else:
            vec = np.zeros(embed_dims, np.float32)
            wrds = word_tokenize(phr)
            for wrd in wrds:
                all_num += 1
                if mode == 'crawl' and wrd in model.vocab:
                    vec += model.word_vec(wrd)
                elif mode == 'kg2vec_ALOD' and (wrd in model.vocab or wrd.lower().replace(' ', '_') in model.vocab):
                    vec += model.vectors[model.vocab[wrd.lower().replace(' ', '_')].index]
                elif mode == 'kg2vec_dbnary' and (
                        'http://kaiko.getalp.org/dbnary/eng/' + wrd.replace(' ', '_') in model.vocab):
                    vec += model.wv.get_vector('http://kaiko.getalp.org/dbnary/eng/' + wrd.replace(' ', '_'))
                elif mode == 'kg2vec_dbpedia' and (
                        'http://dbpedia.org/ontology/' + wrd.replace(' ', '_') in model.vocab or
                        'http://dbpedia.org/resource/' + wrd.replace(' ', '_') in model.vocab):
                    if 'http://dbpedia.org/ontology/' + wrd.replace(' ', '_') in model.vocab:
                        vec += model.wv.get_vector('http://dbpedia.org/ontology/' + wrd.replace(' ', '_'))
                    elif 'http://dbpedia.org/resource/' + wrd.replace(' ', '_') in model.vocab:
                        vec += model.wv.get_vector('http://dbpedia.org/resource/' + wrd.replace(' ', '_'))
                else:
                    vec += np.random.randn(embed_dims)
                    oov_num += 1
            if len(wrds) == 0:
                embed_list.append(vec / 10000)
            else:
                embed_list.append(vec / len(wrds))
    oov_rate = oov_num / all_num
    print('oov rate:', oov_rate, 'oov num:', oov_num, 'all num:', all_num)
    return np.array(embed_list)
