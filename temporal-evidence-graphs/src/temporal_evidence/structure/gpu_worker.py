"""CUDA placement gate writing only extension artifacts."""
import json
from pathlib import Path
import torch
from vllm.v1.worker.gpu_worker import Worker

class StructureGPUWorker(Worker):
    def load_model(self,*args,**kwargs):
        result=super().load_model(*args,**kwargs)
        assert torch.cuda.is_available(), "GPU inference required"
        model=self.model_runner.model; devices={str(p.device) for p in model.parameters()}
        assert devices and all(d.startswith("cuda") for d in devices)
        report={"parameter_devices":sorted(devices),"parameter_count":sum(p.numel() for p in model.parameters()),
            "dtypes":sorted({str(p.dtype) for p in model.parameters()}),"gpu":torch.cuda.get_device_name(),
            "torch":torch.__version__,"cuda":torch.version.cuda,"first_forward_tensor_devices":None}
        path=Path("artifacts/runs/structure_study_v1/gpu_placement.json"); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2)+"\n")
        def hook(module,args,kwargs):
            tensors=[x for x in (*args,*kwargs.values()) if isinstance(x,torch.Tensor)]
            positions={str(x.device) for x in tensors}; assert positions and all(d.startswith("cuda") for d in positions)
            report["first_forward_tensor_devices"]=sorted(positions); path.write_text(json.dumps(report,indent=2)+"\n"); handle.remove()
        handle=model.register_forward_pre_hook(hook,with_kwargs=True)
        return result
