import os, argparse, pickle, codecs, json
from src.helper import checkFile, invertDic
from src.preprocessing import SideInfo  # For processing data and side information
from src.embeddings_multi_view_CL import Embeddings
from collections import defaultdict as ddict


''' *************************************** DATASET PREPROCESSING **************************************** '''


class CMVC_plus_Main(object):

    def __init__(self, args):
        self.p = args
        self.read_triples()

    def read_triples(self):

        fname = self.p.out_path + self.p.file_triples  # File for storing processed triples
        self.triples_list = []  # List of all triples in the dataset
        self.amb_ent = ddict(int)  # Contains ambiguous entities in the dataset
        self.amb_mentions = {}  # Contains all ambiguous mentions
        self.isAcronym = {}  # Contains all mentions which can be acronyms

        print('dataset:', args.dataset)
        if args.dataset == 'OPIEC59k_CL':
            print('load OPIEC_dataset ... ')
            self.triples_list = pickle.load(open(args.data_path, 'rb'))

            ''' Ground truth clustering '''
            self.true_ent2clust = ddict(set)
            for trp in self.triples_list:
                sub_u = trp['triple_unique'][0]
                self.true_ent2clust[sub_u].add(trp['subject_wiki_link'])
            self.true_clust2ent = invertDic(self.true_ent2clust, 'm2os')

        else:
            if not checkFile(fname):
                with codecs.open(args.data_path, encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        trp = json.loads(line.strip())

                        trp['raw_triple'] = trp['triple']
                        sub, rel, obj = map(str, trp['triple'])

                        if len(sub) == 0 or len(rel) == 0 or len(obj) == 0: continue  # Ignore incomplete triples

                        trp['triple'] = [sub, rel, obj]
                        trp['triple_unique'] = [sub + '|' + str(trp['_id']), rel + '|' + str(trp['_id']),
                                                obj + '|' + str(trp['_id'])]
                        trp['ent_lnk_sub'] = trp['entity_linking']['subject']
                        trp['ent_lnk_obj'] = trp['entity_linking']['object']
                        trp['true_sub_link'] = trp['true_link']['subject']
                        trp['true_obj_link'] = trp['true_link']['object']
                        trp['rel_info'] = trp['kbp_info']  # KBP side info for relation

                        self.triples_list.append(trp)

                with open(fname, 'w') as f:
                    f.write('\n'.join([json.dumps(triple) for triple in self.triples_list]))
            else:
                with open(fname) as f:
                    self.triples_list = [json.loads(triple) for triple in f.read().split('\n')]

            ''' Ground truth clustering '''
            self.true_ent2clust = ddict(set)
            for trp in self.triples_list:
                sub_u = trp['triple_unique'][0]
                self.true_ent2clust[sub_u].add(trp['true_sub_link'])
            self.true_clust2ent = invertDic(self.true_ent2clust, 'm2os')

        ''' Identifying ambiguous entities '''
        amb_clust = {}
        for trp in self.triples_list:
            sub = trp['triple'][0]
            for tok in sub.split():
                amb_clust[tok] = amb_clust.get(tok, set())
                amb_clust[tok].add(sub)

        for rep, clust in amb_clust.items():
            if rep in clust and len(clust) >= 3:
                self.amb_ent[rep] = len(clust)
                for ele in clust: self.amb_mentions[ele] = 1

        if args.use_Valid_data:
            print('load valid data')
            fname1 = '../file/' + self.p.dataset + '_' + self.p.split + '/valid_entity'
            if not checkFile(fname1):
                fname = '../data/' + args.dataset + '/' + args.dataset + '_valid'
                if 'OPIEC59k' in args.dataset:
                    valid_triples = pickle.load(open(fname, 'rb'))
                elif 'reverb45k' in args.dataset:
                    valid_triples = []
                    with open(fname, 'rb'):
                        for line in f:
                            trp = json.loads(line.strip())
                            valid_triples.append(trp)

                self.valid_entity = self.get_valid_info(valid_triples)
                pickle.dump(self.valid_entity, open(fname1, 'wb'))
            else:
                self.valid_entity = pickle.load(open(fname1, 'rb'))
            print('self.valid_entity:', len(self.valid_entity))

        print('self.triples_list:', type(self.triples_list), len(self.triples_list))
        print('self.true_clust2ent:', len(self.true_clust2ent))
        print('self.true_ent2clust:', len(self.true_ent2clust))

    def get_sideInfo(self):
        fname = self.p.out_path + self.p.file_sideinfo_pkl

        if not checkFile(fname):
            self.side_info = SideInfo(self.p, self.triples_list)

            del self.side_info.file
            pickle.dump(self.side_info, open(fname, 'wb'))
        else:
            self.side_info = pickle.load(open(fname, 'rb'))

        if self.p.use_Valid_data:
            self.side_info.valid_entity = self.valid_entity
            del self.valid_entity

    def embedKG(self):
        fname1 = self.p.out_path + self.p.file_entEmbed
        fname2 = self.p.out_path + self.p.file_relEmbed

        if not checkFile(fname1) or not checkFile(fname2):
            embed = Embeddings(self.p, self.side_info, true_ent2clust=self.true_ent2clust,
                               true_clust2ent=self.true_clust2ent, triple_list=self.triples_list)
            embed.fit()

            self.ent2embed = embed.ent2embed  # Get the learned NP embeddings
            self.rel2embed = embed.rel2embed  # Get the learned RP embeddings

            pickle.dump(self.ent2embed, open(fname1, 'wb'))
            pickle.dump(self.rel2embed, open(fname2, 'wb'))
        else:
            self.ent2embed = pickle.load(open(fname1, 'rb'))
            self.rel2embed = pickle.load(open(fname2, 'rb'))

    def get_valid_info(self, valid_triples):
        ent2true_link = {}
        for t in valid_triples:
            e1, r, e2 = t['triple']
            if 'OPIEC59k' in self.p.dataset:
                true_link = (t['subject_wiki_link'], t['object_wiki_link'])
            elif 'reverbk' in self.p.dataset:
                true_link = (t['true_link']['subject'], t['true_link']['object'])

            if e1 in ent2true_link.keys():
                ent2true_link[e1].append(true_link[0])
            else:
                ent2true_link[e1] = [true_link[0]]
            if e2 in ent2true_link.keys():
                ent2true_link[e2].append(true_link[1])
            else:
                ent2true_link[e2] = [true_link[1]]

        for ent, true_link in ent2true_link.items():
            if len(true_link) > 1:
                ent2true_link[ent] = max(set(true_link), key=true_link.count)
            else:
                ent2true_link[ent] = true_link[0]
        return ent2true_link


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='CMVC+: A Multi-View Clustering Framework for Open Knowledge Base Canonicalization via Contrastive Learning')
    parser.add_argument('-data', dest='dataset', default='OPIEC59k', help='Dataset to run CMVC+ on')
    parser.add_argument('-split', dest='split', default='CL_test', help='Dataset split for evaluation')
    parser.add_argument('-data_dir', dest='data_dir', default='../data', help='Data directory')
    parser.add_argument('-out_dir', dest='out_dir', default='../output', help='Directory to store CMVC+ output')
    parser.add_argument('-reset', dest="reset", action='store_true', default=True,
                        help='Clear the cached files (Start a fresh run)')
    parser.add_argument('-name', dest='name', default=None, help='Assign a name to the run')
    parser.add_argument('-word2vec_path', dest='word2vec_path', default='../init_dict/crawl-300d-2M.vec',
                        help='word2vec_path')
    parser.add_argument('-alignment_module', dest='alignment_module', default='swapping', help='alignment_module')
    parser.add_argument('-Entity_linking_dict_loc', dest='Entity_linking_dict_loc',
                        default='../init_dict/Entity_linking_dict/Whole_Ranked_Merged_Current_dictionary_UTF-8.txt',
                        help='Location of Entity_linking_dict to be loaded')
    parser.add_argument('-change_EL_threshold', dest='change_EL_threshold', default=False, help='change_EL_threshold')
    parser.add_argument('-entity_EL_threshold', dest='entity_EL_threshold', default=0, help='entity_EL_threshold')
    parser.add_argument('-relation_EL_threshold', dest='relation_EL_threshold', default=0, help='relation_EL_threshold')
    parser.add_argument('--cuda', action='store_true', help='use GPU', default=True)

    # system settings
    parser.add_argument('-embed_init', dest='embed_init', default='crawl', choices=['crawl', 'random'],
                        help='Method for Initializing NP and Relation embeddings')
    parser.add_argument('-embed_loc', dest='embed_loc', default='../init_dict/crawl-300d-2M.vec',
                        help='Location of embeddings to be loaded')

    parser.add_argument('--use_Entity_linking_dict', default=True)
    parser.add_argument('--input', default='entity', choices=['entity', 'relation'])
    parser.add_argument('--entity_threshold', dest='entity_threshold', default=0.9, help='entity_threshold')
    parser.add_argument('--relation_threshold', dest='relation_threshold', default=0.95, help='relation_threshold')

    # fact view
    parser.add_argument('--use_Embedding_model', default=True)
    parser.add_argument('--do_train', action='store_true', default=True)
    parser.add_argument('--fact_cuda', default=0)

    parser.add_argument('--model', default='TransE', type=str)
    parser.add_argument('-embed_dims', dest='embed_dims', default=300, type=int, help='Embedding dimension')
    parser.add_argument('-lr', '--learning_rate', default=0.0001, type=float)

    parser.add_argument('--use_cross_seed', default=True)
    parser.add_argument('--use_soft_learning', default=False)
    parser.add_argument('-cpu', '--cpu_num', default=12, type=int)
    parser.add_argument('-init', '--init_checkpoint', default=None, type=str)

    parser.add_argument('--fact_neg_num', default=1)
    parser.add_argument('--fact_step_size', default=768)
    parser.add_argument('--fact_mlp_dim', default=50)
    parser.add_argument('--conbine_loss', type=bool, default=True)

    parser.add_argument('-de', '--double_entity_embedding', action='store_true', default=False)
    parser.add_argument('-dr', '--double_relation_embedding', action='store_true', default=False)
    parser.add_argument('-n1', '--single_negative_sample_size', default=32, type=int)
    parser.add_argument('-n2', '--cross_negative_sample_size', default=40, type=int)
    parser.add_argument('-d', '--hidden_dim', default=300, type=int)
    parser.add_argument('-g1', '--single_gamma', default=12.0, type=float)
    parser.add_argument('-g2', '--cross_gamma', default=0.0, type=float)
    parser.add_argument('-b1', '--single_batch_size', default=5120, type=int)
    parser.add_argument('-b2', '--cross_batch_size', default=5120, type=int)
    parser.add_argument('-r', '--regularization', default=0.0, type=float)
    parser.add_argument('--uni_weight', action='store_true',
                        help='Otherwise use subsampling weighting like in word2vec', default=True)

    parser.add_argument('--save_checkpoint_steps', default=1000, type=int)
    parser.add_argument('--valid_steps', default=10000, type=int)
    parser.add_argument('--log_steps', default=100, type=int, help='train log every xx steps')
    parser.add_argument('--test_log_steps', default=1000, type=int, help='valid/test log every xx steps')
    parser.add_argument('--max_steps', default=2001, type=int)
    parser.add_argument('--turn_to_seed', default=1000, type=int)
    parser.add_argument('--seed_max_steps', default=2000, type=int)
    parser.add_argument('--warm_up_steps', default=None, type=int)

    # context view
    parser.add_argument('--use_context', default=True)
    parser.add_argument('--replace_h', default=True)
    parser.add_argument('--sentence_delete_stopwords', default=True)
    parser.add_argument('--use_BERT', default=True)
    parser.add_argument('--context_cuda', default=1)

    # Clustering hyper-parameters
    parser.add_argument('-linkage', dest='linkage', default='complete', choices=['complete', 'single', 'average'],
                        help='HAC linkage criterion')
    parser.add_argument('-metric', dest='metric', default='cosine',
                        help='Metric for calculating distance between embeddings')
    parser.add_argument('--step_0_use_hac', default=False)
    args = parser.parse_args()
    if args.name == None: args.name = args.dataset + '_' + args.split + '_' + '1'

    args.file_triples = '/triples.txt'  # Location for caching triples
    args.file_entEmbed = '/embed_ent.pkl'  # Location for caching learned embeddings for noun phrases
    args.file_relEmbed = '/embed_rel.pkl'  # Location for caching learned embeddings for relation phrases
    args.file_entClust = '/cluster_ent.txt'  # Location for caching Entity clustering results
    args.file_relClust = '/cluster_rel.txt'  # Location for caching Relation clustering results
    args.file_sideinfo = '/side_info.txt'  # Location for caching side information extracted for the KG (for display)
    args.file_sideinfo_pkl = '/side_info.pkl'  # Location for caching side information extracted for the KG (binary)
    args.file_results = '/results.json'  # Location for loading hyperparameters

    args.out_path = args.out_dir + '/' + args.name  # Directory for storing output
    print('args.out_path:', args.out_path)
    print('args.reset:', args.reset)
    args.data_path = args.data_dir + '/' + args.dataset + '/' + args.dataset + '_' + args.split  # Path to the dataset
    if args.reset: os.system('rm -r {}'.format(args.out_path))  # Clear cached files if requeste
    if not os.path.isdir(args.out_path): os.system(
        'mkdir -p ' + args.out_path)  # Create the output directory if doesn't exist
    cmvc_plus = CMVC_plus_Main(args)  # Loading KG triples
    cmvc_plus.get_sideInfo()  # Side Information Acquisition
    cmvc_plus.embedKG()  # Learning embedding for Noun and relation phrases
