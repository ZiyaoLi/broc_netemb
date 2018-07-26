import numpy as np
import random
from sklearn.svm import SVC
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.multiclass import OneVsRestClassifier

SHUFFLE = 5
TEST_PERCT = [0.1 * t for t in range(1, 10)]
CROSS_VAL_FOLD = [2, 3, 5, 8, 10]


def read_pairs(filename, sep='\t'):
    pairs = []
    f = open(filename, 'r')
    s = f.readline()
    while len(s):
        pair = s.strip().split(sep)
        left = int(pair[0])
        right = int(pair[1])
        pairs.append((left, right))
        s = f.readline()
    return pairs


def sample_id_mapping(samples, id_map):
    new_samples = []
    for oldVid, label in samples:
        t = id_map[oldVid]
        if isinstance(t, int):
            new_samples.append((t, label))
    return new_samples


def show_results_shuffle(optimizer, micro, macro, train_percentage):
    n_shuffle = micro.shape[1]
    print('Results')
    print('-------------------------------------')
    print('Setting:')
    print('K SIZE:      %d' % optimizer.k_size)
    print('DIMENSION:   %d' % optimizer.dim)
    print('LAMBDA:      %.2f' % optimizer.lam)
    print('ETA:         %.2f' % optimizer.eta)
    print('MAX_ITER:    %d' % optimizer.max_iter)
    print('EPSILON:     %.1e' % optimizer.eps)
    print('GROUPING:    %s' % optimizer.grouping_strategy)
    print('K SAMPLING:  %s' % optimizer.sample_strategy)
    print('-------------------------------------')
    for i, percentage in enumerate(train_percentage):
        print('Train percentage:  %.2f' % (1 - percentage))
        print('Iter           Micro       Macro')
        print('-------------------------------------')
        for ite in range(n_shuffle):
            print('Shuffle #%d:   %.4f      %.4f'
                  % (ite + 1, micro[i, ite], macro[i, ite]))
        print('-------------------------------------')
        print('Average:      %.4f      %.4f'
              % (micro.mean(1)[i], macro.mean(1)[i]))


def show_results_cv(optimizer, micro, macro):
    print('Results')
    print('-------------------------------------')
    print('Setting:')
    print('K SIZE:      %d' % optimizer.k_size)
    print('DIMENSION:   %d' % optimizer.dim)
    print('LAMBDA:      %.2f' % optimizer.lam)
    print('ETA:         %.2f' % optimizer.eta)
    print('MAX_ITER:    %d' % optimizer.max_iter)
    print('EPSILON:     %.1e' % optimizer.eps)
    print('GROUPING:    %s' % optimizer.grouping_strategy)
    print('K SAMPLING:  %s' % optimizer.sample_strategy)
    print('-------------------------------------')
    for i in range(len(micro)):
        print('Train percentage:  %.2f' % (1 - 1 / len(micro[i])))
        print('Fold           Micro       Macro')
        print('-------------------------------------')
        for ite in range(len(micro[i])):
            print('Fold #%d:      %.4f      %.4f'
                  % (ite + 1, micro[i][ite], macro[i][ite]))
        print('-------------------------------------')
        print('Average:      %.4f      %.4f'
              % (np.mean(micro[i]), np.mean(macro[i])))


def multi_class_classification(optimizer, sample_filename, cv=True,
                               test_percentage=TEST_PERCT,
                               cross_val_fold=CROSS_VAL_FOLD,
                               n_shuffle=SHUFFLE):
    graph = optimizer.graph
    samples = read_pairs(sample_filename)
    samples = sample_id_mapping(samples, graph.vid2newVid_mapping)
    random.shuffle(samples)
    x_list = optimizer.embed([t[0] for t in samples])
    x_matrix = np.concatenate(x_list, axis=1).T
    y_list = [t[1] for t in samples]

    if not cv:
        micro_results = np.zeros((len(test_percentage), n_shuffle))
        macro_results = np.zeros((len(test_percentage), n_shuffle))

        for i, percentage in enumerate(test_percentage):
            for ite in range(n_shuffle):
                x_train, x_test, y_train, y_test = train_test_split(
                    x_matrix, y_list,
                    test_size=percentage)
                model = OneVsRestClassifier(SVC())
                model.fit(x_train, y_train)
                pred = model.predict(x_test)

                micro_results[i, ite] = f1_score(y_test, pred, average='micro')
                macro_results[i, ite] = f1_score(y_test, pred, average='macro')

        show_results_shuffle(optimizer, micro_results, macro_results, test_percentage)
    else:
        micro_results = []
        macro_results = []

        for i, k_fold in enumerate(cross_val_fold):
            model = OneVsRestClassifier(SVC())
            micro_results.append(cross_val_score(model, x_matrix, y_list, scoring='f1_micro', cv=k_fold))
            macro_results.append(cross_val_score(model, x_matrix, y_list, scoring='f1_macro', cv=k_fold))

        show_results_cv(optimizer, micro_results, macro_results)
