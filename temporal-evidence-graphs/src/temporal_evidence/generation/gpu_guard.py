"""vLLM worker records real parameter and first-forward tensor placement."""
from pathlib import Path
import json
import torch
from vllm.v1.worker.gpu_worker import Worker


class VerifiedGPUWorker(Worker):
    def load_model(self, *args, **kwargs):
        result=super().load_model(*args,**kwargs)
        assert torch.cuda.is_available(), "CPU inference is prohibited"
        model=self.model_runner.model
        devices={str(parameter.device) for parameter in model.parameters()}
        assert devices and all(device.startswith("cuda") for device in devices),devices
        report={"parameter_devices":sorted(devices),"parameter_count":sum(p.numel() for p in model.parameters()),
                "parameter_dtypes":sorted({str(p.dtype) for p in model.parameters()}),
                "torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(),
                "first_forward_tensor_devices":None}
        path=Path("artifacts/manifests/gpu_placement.json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2)+"\n")
        def inspect_forward(module,args,kwargs):
            tensors=[value for value in (*args,*kwargs.values()) if isinstance(value,torch.Tensor)]
            tensor_devices={str(value.device) for value in tensors}
            assert tensors and all(device.startswith("cuda") for device in tensor_devices),tensor_devices
            report["first_forward_tensor_devices"]=sorted(tensor_devices)
            path.write_text(json.dumps(report,indent=2)+"\n")
            handle.remove()
        handle=model.register_forward_pre_hook(inspect_forward,with_kwargs=True)
        return result
