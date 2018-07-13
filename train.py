
# please notice that @ operator is for matrix multiplication

# for A = (a1, a2, ..., an) where a_i are column vectors,
#     B = (b1, b2, ..., bn) with the same shape, the function
#     sum(A * B) gives the vector
#             (<a1, b1>, <a2, b2>, ..., <an, bn>).

import numpy as np
from numpy.linalg import norm
from graph import Graph
from sample import sample


LAMBDA = 0.5
ETA = 0
MAX_ITER = 100
CG_MAX_ITER = 20
EPSILON = 1e-4
CG_EPSILON = 1e-8
DIMENSION = 2
K_SIZE = 3


def conjugate_gradient(x, A, b, max_iter=CG_MAX_ITER, eps=EPSILON):
    '''
    Implemented from algorithm CG for SPD matrix linear equations,
    from XU, Shufang, et. Numerical Linear Algebra.
    :param x: initial value x0. Can be matrix of size (n x p) for a
              p-parallel CG.
    :param A: matrix in problem Ax = b.
    :param b: vector(matrix) in problem Ax = b. Notice that b \in R^(n x p).
    :param max_iter: max iterations
    :param eps: stop criterion
    :return: optimized x
    '''
    b_norms = sum(b * b)
    criterion = eps * b_norms
    ite = 0
    r = b - A @ x
    rho = sum(r * r)
    while ite < max_iter and (rho > criterion).any():
        ite += 1
        if ite == 1:
            p = r
        else:
            beta = rho / rho_tilde
            p = r + beta * p

        w = A @ p
        alpha = rho / sum(p * w)
        x = x + alpha * p
        r = r - alpha * w
        rho_tilde = rho
        rho = sum(r * r)
    return x


class Optimizer:
    def __init__(self, graph, groups,
                 dim=DIMENSION,
                 lam=LAMBDA, eta=ETA,
                 max_iter=MAX_ITER, epsilon=CG_EPSILON):
        self.graph = graph
        self.groups = groups
        self.nGroups = len(groups)
        self.lam = lam
        self.eta = eta
        self.max_iter = max_iter
        self.eps = epsilon

        # k decomposition: SVD
        self.m_0_all = self.graph.calc_matrix(groups[0], list(range(graph.nVertices)))
        self.m_all_0 = self.graph.calc_matrix(list(range(graph.nVertices)), groups[0])
        m0 = self.m_0_all[:, groups[0]]
        u, d, v = np.linalg.svd(m0)
        self.phi = (u[:, :dim] @ np.diag(np.sqrt(d[:dim]))).T
        self.psi = (v.T[:, :dim] @ np.diag(np.sqrt(d[:dim]))).T
        self.m0_tilde = self.phi.T @ self.psi

    def _get_rest_idx(self, group_idx):
        ib = []
        for i in range(1, len(self.groups)):
            if i == group_idx:
                continue
            ib += self.groups[i]
        return ib

    def train(self, group_idx):

        assert group_idx < self.nGroups
        if group_idx == 0:
            return self.phi, self.psi

        indices = self.groups[group_idx]
        rest_indices = self._get_rest_idx(group_idx)

        # pre-calculate the matrices and intercepts to be used
        # to minimize the efforts in the loop.

        # 1.t_mm: \tilde{m_0} * \tilde{m_0}^T
        t_mm = self.m0_tilde @ self.m0_tilde.T

        # 2. pre-calculate constants for A
        m_1_0 = self.m_all_0[indices, :]
        m_0_r = self.m_0_all[:, rest_indices]
        m_1_r = self.graph.calc_matrix(self.groups[group_idx], rest_indices)
        # G_A = G0_A + G(B), b_A = b0_A + b(B),
        # where G(B) and b(B) are the B-related additive factors.
        G0_A = t_mm + self.lam * (m_0_r @ m_0_r.T) + self.eta * np.eye(len(t_mm))
        b0_A = self.m0_tilde @ m_1_0.T + self.lam * (m_0_r @ m_1_r.T)
        # delete useless variables in time.
        del m_1_r

        # 3. duel process for B
        m_0_1 = self.m_0_all[:, indices]
        m_r_0 = self.m_all_0[rest_indices, :]
        m_r_1 = self.graph.calc_matrix(rest_indices, self.groups[group_idx])
        G0_B = t_mm.T + self.lam * (m_r_0.T @ m_r_0) + self.eta * np.eye(len(t_mm))
        b0_B = self.m0_tilde.T @ m_0_1 + self.lam * (m_r_0.T @ m_r_1)
        del m_r_1

        del t_mm, rest_indices

        # 4. m_1_1
        m_1_1 = self.graph.calc_matrix(self.groups[group_idx], self.groups[group_idx])

        # init
        n_0 = len(self.groups[0])
        n_1 = len(self.groups[group_idx])
        # random initial values
        A_prev = np.random.random((n_0, n_1))
        B_prev = np.random.random((n_0, n_1))
        # zero initial values
        # A_prev = np.zeros((n_0, n_1))
        # B_prev = np.zeros((n_0, n_1))
        ite = 0
        altered = np.inf  # initial 'altered' doesn't stop the loop
        while ite < self.max_iter and altered > self.eps:
            ite += 1
            # fix B update A
            t_mb = self.m0_tilde @ B_prev
            G_A = G0_A + t_mb @ t_mb.T
            b_A = b0_A + t_mb @ m_1_1.T
            A = conjugate_gradient(A_prev, G_A, b_A, self.max_iter)
            del t_mb, G_A, b_A

            # fix A update B
            t_ma = self.m0_tilde.T @ A_prev
            G_B = G0_B + t_ma @ t_ma.T
            b_B = b0_B + t_ma @ m_1_1
            B = conjugate_gradient(A_prev, G_B, b_B, self.max_iter)
            del t_ma, G_B, b_B

            altered = norm(A - A_prev, np.inf) + norm(B - B_prev, np.inf)
            A_prev = A
            B_prev = B

        w = self.phi @ A
        c = self.psi @ B

        # debug info
        # original = net.calc_matrix(self.groups[0] + self.groups[group_idx],
        #                            self.groups[0] + self.groups[group_idx])
        # reconstruct = np.concatenate([self.phi, w], 1).T @ \
        #               np.concatenate([self.psi, c], 1)
        # delta = abs(original - reconstruct)
        #
        # t = norm(delta)

        return w, c
        
    # def get_embeddings(self):
    #     embeddings = {}
    #     for i, v in enumerate(self.groups[0]) :
    #         embeddings[v] = self.wt[i].tolist()
    #     print("{} Blocks in All".format(len(self.groups)))
    #     for index in range(1, len(self.groups)) :
    #         self.train(index, embeddings)
    #         print("Block {} Finished!".format(index))
    #     return embeddings

if __name__ == '__main__':
    net = Graph('sample.txt', typ=1)
    k_set = sample(net, k=3, method='deg^2')
    sep = [[3, 4, 7], [1, 0, 6], [2, 8], [5, 9]]
    model = Optimizer(net, sep, dim=2)
    vecs_w = []
    vecs_c = []
    for t in range(4):
        w, c = model.train(t)
        vecs_w.append(w)
        vecs_c.append(c)

    # concatenate all the derived vectors together
    ws = np.concatenate(vecs_w, 1)
    cs = np.concatenate(vecs_c, 1)

    # reconstructing matrix over the order of sampled vertices
    reconstruct = ws.T @ cs
    all_idx = sep[0] + sep[1] + sep[2] + sep[3]
    original = net.calc_matrix(all_idx, all_idx)

    # evaluate the reconstruction performance
    delta = original - reconstruct
    abs_delta = abs(delta)
    t = norm(delta, 'fro')
    tt = norm(original, 'fro')
    print("Original - %.4f, delta - %.4f, percentage - %.4f"
          % (tt, t, t / tt))



