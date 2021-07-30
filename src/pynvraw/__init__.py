'''User-facing API for working with pynvraw.'''
from .nvapi_api import NvAPI
from .status import NvError, NvStatus

from .gpu import Gpu, Clocks

api = NvAPI()

def get_phys_gpu(cuda_dev: int) -> Gpu:
    from .cuda_api import get_cuda_bus_slot
    busId, slotId = get_cuda_bus_slot(cuda_dev)

    return Gpu(api.get_gpu_by_bus(busId, slotId), api)

def get_gpus():
    try:
        return get_gpus._gpu_cache
    except AttributeError:
        get_gpus._gpu_cache = tuple(Gpu(g, api) for g in api.gpu_handles)
        return get_gpus._gpu_cache

__all__ = ['api', 'Gpu', 'Clocks', 'NvError', 'NvStatus', 'get_phys_gpu', 'get_gpus']
