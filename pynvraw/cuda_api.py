'''Module for working with CUDA API.'''

import ctypes
import typing

cuda = ctypes.CDLL('nvcuda.dll')

CU_DEVICE_ATTRIBUTE_PCI_BUS_ID = 33
CU_DEVICE_ATTRIBUTE_PCI_DEVICE_ID = 34

cuInit = cuda.cuInit
cuInit.restype = ctypes.c_int
cuInit.argtypes = [ctypes.c_int]

cuDeviceGetAttribute = cuda.cuDeviceGetAttribute
cuDeviceGetAttribute.restype = ctypes.c_int
cuDeviceGetAttribute.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int]

def _init_cuda():
    res = cuInit(0)
    if res != 0:
        raise RuntimeError(f'Cannot initialize CUDA: {res}', res)

def _get_cuda_attr(dev: int, attr: int) -> int:
    value = ctypes.c_int(-1)
    res = cuDeviceGetAttribute(ctypes.pointer(value), attr, dev)
    if res != 0:
        raise ValueError(f'Can not get CUDA attribute {attr}: {res}', res)
    return value.value

def get_cuda_bus_slot(dev: int) -> typing.Tuple[int, int]:
    '''Reads bus id and slot id for given CUDA device.'''
    busId = _get_cuda_attr(dev, CU_DEVICE_ATTRIBUTE_PCI_BUS_ID)
    slotId = _get_cuda_attr(dev, CU_DEVICE_ATTRIBUTE_PCI_DEVICE_ID)
    return busId, slotId

_init_cuda()
