"""Artifact serialization; compact weights omit original distance adjacency."""
import csv
import gzip
import json
from pathlib import Path
import torch


def read(path):return json.loads(Path(path).read_text())


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    def convert(v):
        if isinstance(v,torch.Tensor):return v.detach().cpu().tolist()
        if isinstance(v,dict):return {k:convert(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):return [convert(x) for x in v]
        return v
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(convert(value),indent=2,allow_nan=False)+'\n');temporary.replace(path)


def save_weights(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as out:torch.save(value,out)


def load_weights(path):
    with gzip.open(path,'rb') as stream:return torch.load(stream,map_location='cuda',weights_only=True)


def compact_state(model):
    return {k:v.detach().clone() for k,v in model.state_dict().items() if k not in ('W','P','blocks')}


def restore_state(model,state):
    missing,unexpected=model.load_state_dict(state,strict=False)
    assert set(missing)=={'W','P','blocks'} and not unexpected,(missing,unexpected)
    model.eval();return model


def save_predictions(path,part,predictions):
    fields={k:part[k].detach().cpu().tolist() for k in ('origins','time_ns','day','y','lower','upper','eligible','active','coverage')}
    fields.update({k:v.detach().cpu().tolist() for k,v in predictions.items()})
    with gzip.open(path,'wt',newline='') as out:
        writer=csv.writer(out,lineterminator='\n');writer.writerow(fields);writer.writerows(zip(*fields.values()))
