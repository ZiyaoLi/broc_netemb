from graph import Graph
from sample import sample
from train import Optimizer
from group import Louvain, groups2inv_index, pure_override_nodes
import numpy as np
from numpy.linalg import norm

K_SIZE = 400
DIMENSION = 100
VERBOSE = 2
GROUP_IGNORE = 1
SAMPLE_METHOD = 'deg^2|group_prob'
RANDOM_GROUPING = True

MATRIX_TO_FILE = False
FILE_NAME = 'wiki_200k_100d_l0.8_e0.1_theta1_prob.csv'

net = Graph('wiki.txt', typ=1)
grouping_model = Louvain(net)
groups = grouping_model.execute(rand=RANDOM_GROUPING)
group_sizes = [len(t) for t in groups]
inv_index_original = groups2inv_index(groups, net.nVertices)
sizes_index = [group_sizes[t - 1] for t in inv_index_original]

# k_set = sample(net, k=K_SIZE, method='deg_deter')
k_set = sample(net, k=K_SIZE, method=SAMPLE_METHOD, size_index=sizes_index)

inv_index = groups2inv_index(groups, net.nVertices, k_set)
pure_override_nodes(groups, inv_index)
groups = [k_set] + groups
model = Optimizer(net, groups, dim=DIMENSION)
vecs_w = []
vecs_c = []

all_idx = []
for t in range(len(groups)):
    if len(groups[t]) <= GROUP_IGNORE:
        continue
    print("%d / %d, n_vertices = %d..., accumul_vertex = %d "
          % (t + 1, len(groups), len(groups[t]), len(all_idx)))
    w, c = model.train(t, verbose=VERBOSE)
    vecs_w.append(w)
    vecs_c.append(c)
    all_idx += groups[t]

# concatenate all the derived vectors together
ws = np.concatenate(vecs_w, 1)
cs = np.concatenate(vecs_c, 1)

# reconstructing matrix over the order of sampled vertices
reconstruct = ws.T @ cs
original = net.calc_matrix(all_idx, all_idx)

# evaluate the reconstruction performance
delta = original - reconstruct
abs_delta = abs(delta)
if MATRIX_TO_FILE:
    np.savetxt(FILE_NAME, abs_delta, '%.6e', ',', '\n')
t = norm(delta, 'fro')
tt = norm(original, 'fro')
print("Original - %.4f, delta - %.4f, percentage - %.4f"
      % (tt, t, t / tt))

# a SVD implementation to exam how good is the result
u, d, v = np.linalg.svd(original)
w_svd = (u[:, :DIMENSION] * np.sqrt(d[:DIMENSION])).T
c_svd = (v.T[:, :DIMENSION] * np.sqrt(d[:DIMENSION])).T
reconstruct_svd = w_svd.T @ c_svd
delta_svd = original - reconstruct_svd
t_svd = norm(delta_svd, 'fro')
print("Original - %.4f, delta - %.4f, percentage - %.4f"
      % (tt, t_svd, t_svd / tt))
