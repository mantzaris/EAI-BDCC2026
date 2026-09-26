"""Frozen GPU quantile boosting, explicitly NOT sklearn's historical model."""
import torch


class GPUQuantileBoost:
    def __init__(self, config):
        self.config = config
        self.trees = []

    def bins(self, X):
        assert X.is_cuda and torch.isfinite(X).all()
        return torch.searchsorted(self.cuts, X.T.contiguous(), right=False).T.to(torch.int16)

    def fit(self, X, y):
        assert X.is_cuda and y.is_cuda and not self.trees
        X, y = X.double(), y.double()
        c = self.config
        self.cuts = torch.quantile(X, torch.arange(1, c['max_bins'], device=X.device).double()/c['max_bins'], dim=0).T.contiguous()
        binned = self.bins(X)
        self.intercept = torch.logit(y.mean().clamp(1e-6, 1-1e-6))
        score = self.intercept.expand(len(y)).clone()
        F, K = X.shape[1], c['max_bins']

        def candidate(ids, gradient, hessian):
            value = gradient[ids].sum()/(hessian[ids].sum()+c['l2'])*c['learning_rate']
            node = dict(ids=ids, value=value, gain=X.new_tensor(-torch.inf), feature=0, cut=0, left=0, right=0)
            if ids.numel() < 2*c['min_leaf']:
                return node
            ix = binned[ids].T.long()
            hist = []
            for weight in (gradient[ids], hessian[ids], torch.ones_like(gradient[ids])):
                hist.append(X.new_zeros(F, K).scatter_add_(1, ix, weight.expand(F, -1)).cumsum(1))
            g, h, n = hist
            gr, hr, nr = g[:, -1:]-g, h[:, -1:]-h, n[:, -1:]-n
            gain = g.square()/(h+c['l2'])+gr.square()/(hr+c['l2'])-g[:, -1:].square()/(h[:, -1:]+c['l2'])
            gain = gain.masked_fill((n<c['min_leaf'])|(nr<c['min_leaf'])|(h<1e-8)|(hr<1e-8), -torch.inf)
            best = gain.argmax()
            node.update(gain=gain.flatten()[best], feature=int((best//K).item()), cut=int((best%K).item()))
            return node

        for iteration in range(c['trees']):
            p = score.sigmoid()
            gradient, hessian = y-p, (p*(1-p)).clamp_min(1e-8)
            nodes = [candidate(torch.arange(len(y), device=X.device), gradient, hessian)]
            leaves = [0]
            for _ in range(c['max_leaves']-1):
                which = int(torch.stack([nodes[i]['gain'] for i in leaves]).argmax().item())
                j = leaves[which]; node = nodes[j]
                if not bool((node['gain']>0).item()):
                    break
                ids = node['ids']; left = binned[ids, node['feature']]<=node['cut']
                node['left'], node['right'] = len(nodes), len(nodes)+1
                nodes.extend([candidate(ids[left], gradient, hessian), candidate(ids[~left], gradient, hessian)])
                leaves[which:which+1] = [node['left'], node['right']]
            leaf_flag = torch.zeros(len(nodes), dtype=torch.bool, device=X.device)
            for j in leaves:
                score[nodes[j]['ids']] += nodes[j]['value']
                leaf_flag[j] = True
            tree = {k:torch.tensor([n[k] for n in nodes], device=X.device, dtype=torch.long) for k in ('feature','cut','left','right')}
            tree['value'] = torch.stack([n['value'] for n in nodes])
            tree['leaf'] = leaf_flag
            self.trees.append(tree)
        return self

    @torch.no_grad()
    def predict(self, X):
        binned = self.bins(X.double())
        score = self.intercept.expand(len(X)).clone()
        row = torch.arange(len(X), device=X.device)
        for tree in self.trees:
            node = torch.zeros(len(X), device=X.device, dtype=torch.long)
            # A binary tree with <=L leaves has depth <=L-1. Leaf indices stay fixed.
            for _ in range(self.config['max_leaves']-1):
                go_left = binned[row, tree['feature'][node]] <= tree['cut'][node]
                child = torch.where(go_left, tree['left'][node], tree['right'][node])
                node = torch.where(tree['leaf'][node], node, child)
            assert tree['leaf'][node].all()
            score += tree['value'][node]
        return score.sigmoid()

    def state_dict(self):
        return dict(config=self.config, cuts=self.cuts, intercept=self.intercept, trees=self.trees)

    @classmethod
    def from_state(cls, state):
        model = cls(state['config'])
        model.cuts, model.intercept, model.trees = state['cuts'], state['intercept'], state['trees']
        assert model.cuts.is_cuda
        return model


class SavedBaseline:
    """Exact saved predictions on known origins; cannot invent unseen inference."""
    def __init__(self, origins, probability):
        assert origins.is_cuda and probability.is_cuda
        order = origins.argsort()
        self.origins, self.probability = origins[order], probability[order].double()

    def predict(self, origins):
        indices = torch.searchsorted(self.origins, origins)
        assert (indices < len(self.origins)).all()
        assert torch.equal(self.origins[indices], origins)
        return self.probability[indices]
