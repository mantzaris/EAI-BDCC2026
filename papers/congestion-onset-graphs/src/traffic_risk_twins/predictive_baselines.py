"""Small training-fitted baselines with explicit information differences."""
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import HistGradientBoostingClassifier


def features(history,mask,blocks,calendar,kind):
    block_mean=[]; counts=[]; extras=[]
    for b in np.unique(blocks):
        values=history[:,:,blocks == b]
        valid=mask[:,:,blocks == b]
        count=valid.sum(axis=-1)
        mean=np.where(valid,values,0).sum(axis=-1)/np.maximum(count,1)
        block_mean.append(mean); counts.append(count)
        if kind == 'heterogeneity':
            variance=np.where(valid,(values-mean[:,:,None])**2,0).sum(axis=-1)/np.maximum(count,1)
            minimum=np.where(valid,values,np.inf).min(axis=-1)
            maximum=np.where(valid,values,-np.inf).max(axis=-1)
            severe=((values >= 0)&valid).sum(axis=-1)/np.maximum(count,1)
            extras.extend([variance,np.where(np.isfinite(minimum),minimum,0),np.where(np.isfinite(maximum),maximum,0),severe])
    means=np.stack(block_mean,axis=-1)
    count=np.stack(counts,axis=-1)
    if kind == 'seasonal_persistence':
        return np.concatenate([means[:,-1],means[:,-1]-means[:,-3],count[:,-1],calendar],axis=1)
    arrays=[means.reshape(len(history),-1),count.reshape(len(history),-1),calendar]
    if extras: arrays.append(np.stack(extras,axis=-1).reshape(len(history),-1))
    return np.concatenate(arrays,axis=1)


def fit_predict(X,y,Xval,kind):
    if len(np.unique(y)) == 1:
        return np.full(len(Xval),(y.sum()+.5)/(len(y)+1)),None
    if kind == 'heterogeneity':
        model=HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=15,l2_regularization=10.,random_state=20260922)
    else:
        model=make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=1000,solver='lbfgs'))
    model.fit(X,y)
    return model.predict_proba(Xval)[:,1],model
