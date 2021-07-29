'''Low-level API working through obscure nvapi.dll.'''

import ctypes
import typing
import sys

from .status import NvStatus, NvError, NVAPI_OK

nvapi = ctypes.CDLL('nvapi64.dll' if sys.maxsize > 2**32 else 'nvapi.dll')

_nvapi_QueryInterface = nvapi.nvapi_QueryInterface
_nvapi_QueryInterface.restype = ctypes.c_void_p
_nvapi_QueryInterface.argtypes = [ctypes.c_int]

NVAPI_MAX_PHYSICAL_GPUS = 64
NVAPI_MAX_THERMAL_SENSORS_PER_GPU = 3

NVAPI_THERMAL_TARGET_GPU = 1
NVAPI_THERMAL_TARGET_ALL = 15

NVAPI_SHORT_STRING_MAX = 64

NVAPI_COOLER_POLICY_USER = 1
NVAPI_MAX_GPU_PUBLIC_CLOCKS = 32

NV_GPU_CLOCK_FREQUENCIES_CURRENT_FREQ = 0
NV_GPU_CLOCK_FREQUENCIES_BASE_CLOCK = 1
NV_GPU_CLOCK_FREQUENCIES_BOOST_CLOCK = 2

NVAPI_GPU_PUBLIC_CLOCK_GRAPHICS = 0
NVAPI_GPU_PUBLIC_CLOCK_MEMORY = 4
NVAPI_GPU_PUBLIC_CLOCK_PROCESSOR = 7
NVAPI_GPU_PUBLIC_CLOCK_VIDEO = 8

NVAPI_MAX_GPU_PSTATE20_PSTATES = 16
NVAPI_MAX_GPU_PSTATE20_CLOCKS = 8
NVAPI_MAX_GPU_PSTATE20_BASE_VOLTAGES = 4

NvAPI_ShortString = ctypes.c_char * NVAPI_SHORT_STRING_MAX

class NvPhysicalGpu(ctypes.Structure):
    _pack_ = 8
    _fields_ = [('unused', ctypes.c_int), 
                ('pad', ctypes.c_int8)]
NV_ENUM_GPUS = NvPhysicalGpu * NVAPI_MAX_PHYSICAL_GPUS

class NvVersioned(ctypes.Structure):
    def __init__(self):
        self.version = ctypes.sizeof(self) + (self._nv_version_ << 16)

class NV_THERMAL_SENSOR(ctypes.Structure):
    _fields_ = [('controller', ctypes.c_int),
                ('defaultMinTemp', ctypes.c_int32),
                ('defaultMaxTemp', ctypes.c_int32),
                ('currentTemp', ctypes.c_int32),
                ('target', ctypes.c_int)]

class NV_GPU_THERMAL_SETTINGS(NvVersioned):
    _nv_version_ = 2
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('sensor', NV_THERMAL_SENSOR * NVAPI_MAX_THERMAL_SENSORS_PER_GPU)]

class NV_GPU_THERMAL_EX(NvVersioned):
    _nv_version_ = 2
    _pack_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('mask', ctypes.c_uint32),
                ('pad', ctypes.c_uint32 * 8),
                ('_sensors', ctypes.c_uint32 * 32)]
    @property
    def sensors(self):
        return tuple(x / 256.0 for x in self._sensors)

class _NvCoolerLevel(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('level', ctypes.c_uint32),
                ('policy', ctypes.c_uint32)]

class NvCoolerLevels(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('levels', _NvCoolerLevel * 20)]

class NV_SINGLE_COOLER(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32),
                ('controller', ctypes.c_int32),
                ('default_min', ctypes.c_int32),
                ('default_max', ctypes.c_int32),
                ('current_min', ctypes.c_int32),
                ('current_max', ctypes.c_int32),
                ('current_level', ctypes.c_int32),
                ('default_policy', ctypes.c_int32),
                ('current_policy', ctypes.c_int32),
                ('target', ctypes.c_int32),
                ('control_type', ctypes.c_int32),
                ('active', ctypes.c_int32)]

class NV_GPU_COOLER_SETTINGS(NvVersioned):
    _nv_version_ = 2
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('coolers', NV_SINGLE_COOLER * 20)]

class NV_GPU_CLOCK_DOMAIN(ctypes.Structure):
    _fields_ = [('bIsPresent', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('frequency', ctypes.c_uint32)]

class NV_GPU_CLOCK_FREQUENCIES(NvVersioned):
    _nv_version_ = 3
    _fields_ = [('version', ctypes.c_uint32),
                ('ClockType', ctypes.c_uint32, 4),
                ('reserved', ctypes.c_uint32, 20),
                ('reserved1', ctypes.c_uint32, 8),
                ('domain', NV_GPU_CLOCK_DOMAIN * NVAPI_MAX_GPU_PUBLIC_CLOCKS)]

class NV_GPU_CLOCKS_INFO(NvVersioned):
    _nv_version_ = 2
    _fields_ = [('version', ctypes.c_uint32),
                ('clocks', ctypes.c_uint32 * 288)]

class NV_GPU_PERF_PSTATES20_PARAM_DELTA(ctypes.Structure):
    _fields_ = [('value', ctypes.c_int32),
                ('valueMin', ctypes.c_int32),
                ('valueMax', ctypes.c_int32)]

class _NV_GPU_PSTATE_DATA_RANGE(ctypes.Structure):
    _fields_ = [('minFreq_kHz', ctypes.c_uint32),
                ('maxFreq_kHz', ctypes.c_uint32),
                ('domainId', ctypes.c_int),
                ('minVoltage_uV', ctypes.c_uint32),
                ('maxVoltage_uV', ctypes.c_uint32)]

class _NV_GPU_PSTATE_DATA_U(ctypes.Union):
    _fields_ = [('single_freq_kHz', ctypes.c_uint32),
                ('range', _NV_GPU_PSTATE_DATA_RANGE)]

class NV_GPU_PSTATE20_CLOCK_ENTRY_V1(ctypes.Structure):
    _fields_ = [('domainId', ctypes.c_int),
                ('typeId', ctypes.c_int),
                ('bIsEditable', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('freqDelta_kHz', NV_GPU_PERF_PSTATES20_PARAM_DELTA),
                ('data', _NV_GPU_PSTATE_DATA_U)]

class NV_GPU_PSTATE20_BASE_VOLTAGE_ENTRY_V1(ctypes.Structure):
    _fields_ = [('domainId', ctypes.c_int),
                ('bIsEditable', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('volt_uV', ctypes.c_uint32),
                ('voltDelta_uV', NV_GPU_PERF_PSTATES20_PARAM_DELTA)]

class _NV_GPU_PSTATE(ctypes.Structure):
    _fields_ = [('pstateId', ctypes.c_int),
                ('bIsEditable', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('clocks', NV_GPU_PSTATE20_CLOCK_ENTRY_V1 * NVAPI_MAX_GPU_PSTATE20_CLOCKS),
                ('baseVoltages', NV_GPU_PSTATE20_BASE_VOLTAGE_ENTRY_V1 * NVAPI_MAX_GPU_PSTATE20_BASE_VOLTAGES)]

class _NV_GPU_OVERVOLT(ctypes.Structure):
    _fields_ = [('numVoltages', ctypes.c_uint32),
                ('voltages', NV_GPU_PSTATE20_BASE_VOLTAGE_ENTRY_V1 * NVAPI_MAX_GPU_PSTATE20_BASE_VOLTAGES)]

class NV_GPU_PERF_PSTATES20_INFO(NvVersioned):
    _nv_version_ = 2
    _fields_ = [('version', ctypes.c_uint32),
                ('bIsEditable', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('numPstates', ctypes.c_uint32),
                ('numClocks', ctypes.c_uint32),
                ('numBaseVoltages', ctypes.c_uint32),
                ('pstates', _NV_GPU_PSTATE * NVAPI_MAX_GPU_PSTATE20_PSTATES),
                ('ov', _NV_GPU_OVERVOLT)]

class _NV_GPU_POWER_INFO_ENTRY(ctypes.Structure):
    _fields_ = [('pstate', ctypes.c_uint32),
                ('pad0', ctypes.c_uint32 * 2),
                ('min_power', ctypes.c_uint32),
                ('pad1', ctypes.c_uint32 * 2),
                ('def_power', ctypes.c_uint32),
                ('pad2', ctypes.c_uint32 * 2),
                ('max_power', ctypes.c_uint32),
                ('pad3', ctypes.c_uint32)]

class NV_GPU_POWER_INFO(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('valid', ctypes.c_uint8),
                ('count', ctypes.c_uint8),
                ('padding', ctypes.c_uint8 * 2),
                ('entries', _NV_GPU_POWER_INFO_ENTRY * 4)]

class _NV_GPU_POWER_STATUS_ENTRY(ctypes.Structure):
    _fields_ = [('pad0', ctypes.c_uint32),
                ('pad1', ctypes.c_uint32),
                ('power', ctypes.c_uint32),
                ('pad2', ctypes.c_uint32)]

class NV_GPU_POWER_STATUS(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('entries', _NV_GPU_POWER_STATUS_ENTRY * 4)]

class NV_GPU_TOPOLOGY_STATUS(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('unknown', ctypes.c_uint32 * 16)]

class Method:
    def __init__(self, offset, restype, *argtypes):
        self.proto = ctypes.CFUNCTYPE(restype, *argtypes, use_errno=True, use_last_error=True)
        self.offset = offset
        self.func = None

    def __call__(self, *args):
        if self.func is None:
            addr = _nvapi_QueryInterface(self.offset)
            if addr == 0:
                raise RuntimeError(f'Cannot get nvapi function by offset {self.offset}')
            self.func = self.proto(addr)
        return self.func(*args)

class NvMethod(Method):
    def __init__(self, offset, name, *argtypes, allowed_returns=()):
        super().__init__(offset, ctypes.c_int, *argtypes)
        self.name = name
        self.allowed_returns = set(NvStatus.cast(x) for x in allowed_returns) | set([NVAPI_OK])

    def __call__(self, *args):
        result = NvStatus.by_value(super().__call__(*args))
        if result in self.allowed_returns:
            return result
        raise NvError(f'Error in {self.name}: {result}', result)


class NvAPI:
    NvAPI_Initialize = NvMethod(0x0150E828, 'NvAPI_Initialize')
    NvAPI_Unload = NvMethod(0xD22BDD7E, 'NvAPI_Unload')
    NvAPI_EnumPhysicalGPUs = NvMethod(0xE5AC921F, 'NvAPI_EnumPhysicalGPUs', NV_ENUM_GPUS, ctypes.POINTER(ctypes.c_int))
    NvAPI_GPU_GetBusId = NvMethod(0x1BE0B8E5, 'NvAPI_GPU_GetBusId', NvPhysicalGpu, ctypes.POINTER(ctypes.c_uint32))
    NvAPI_GPU_GetBusSlotId = NvMethod(0x2A0A350F, 'NvAPI_GPU_GetBusSlotId', NvPhysicalGpu, ctypes.POINTER(ctypes.c_uint32))
    NvAPI_GPU_GetThermalSettings = NvMethod(0xE3640A56, 'NvAPI_GPU_GetThermalSettings', NvPhysicalGpu, ctypes.c_uint32, ctypes.POINTER(NV_GPU_THERMAL_SETTINGS))
    NvAPI_GPU_GetAllTempsEx = NvMethod(0x65FE3AAD, 'NvAPI_GPU_GetAllTempsEx', NvPhysicalGpu, ctypes.POINTER(NV_GPU_THERMAL_EX))
    NvAPI_GPU_GetFullName = NvMethod(0xCEEE8E9F, 'NvAPI_GPU_GetFullName', NvPhysicalGpu, ctypes.POINTER(NvAPI_ShortString))
    NvAPI_GPU_SetCoolerLevels = NvMethod(0x891FA0AE, 'NvAPI_GPU_SetCoolerLevels', NvPhysicalGpu, ctypes.c_int32, ctypes.POINTER(NvCoolerLevels))
    NvAPI_GPU_GetCoolerSettings = NvMethod(0xDA141340, 'NvAPI_GPU_GetCoolerSettings', NvPhysicalGpu, ctypes.c_int32, ctypes.POINTER(NV_GPU_COOLER_SETTINGS))
    NvAPI_GPU_GetAllClockFrequencies = NvMethod(0xDCB616C3, 'NvAPI_GPU_GetAllClockFrequencies', NvPhysicalGpu, ctypes.POINTER(NV_GPU_CLOCK_FREQUENCIES))
    NvAPI_GPU_GetAllClocks = NvMethod(0x1BD69F49, 'NvAPI_GPU_GetAllClocks', NvPhysicalGpu, ctypes.POINTER(NV_GPU_CLOCKS_INFO))
    NvAPI_GPU_RestoreCoolerSettings = NvMethod(0x8F6ED0FB, 'NvAPI_GPU_RestoreCoolerSettings', NvPhysicalGpu, ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32)
    NvAPI_GPU_GetPstates20 = NvMethod(0x6FF81213, 'NvAPI_GPU_GetPstates20', NvPhysicalGpu, ctypes.POINTER(NV_GPU_PERF_PSTATES20_INFO))
    NvAPI_GPU_SetPstates20 = NvMethod(0x0F4DAE6B, 'NvAPI_GPU_SetPstates20', NvPhysicalGpu, ctypes.POINTER(NV_GPU_PERF_PSTATES20_INFO))
    NvAPI_GPU_ClientPowerPoliciesGetInfo = NvMethod(0x34206D86, 'NvAPI_GPU_ClientPowerPoliciesGetInfo', NvPhysicalGpu, ctypes.POINTER(NV_GPU_POWER_INFO))
    NvAPI_GPU_ClientPowerPoliciesGetStatus = NvMethod(0x70916171, 'NvAPI_GPU_ClientPowerPoliciesGetStatus', NvPhysicalGpu, ctypes.POINTER(NV_GPU_POWER_STATUS))
    NvAPI_GPU_ClientPowerPoliciesSetStatus = NvMethod(0xAD95F5ED, 'NvAPI_GPU_ClientPowerPoliciesSetStatus', NvPhysicalGpu, ctypes.POINTER(NV_GPU_POWER_STATUS))
    NvAPI_GPU_ClientPowerTopologyGetStatus = NvMethod(0xEDCF624E, 'NvAPI_GPU_ClientPowerTopologyGetStatus', NvPhysicalGpu, ctypes.POINTER(NV_GPU_TOPOLOGY_STATUS))

    def __init__(self):
        self.NvAPI_Initialize()
        self.__gpus = None

    def __del__(self):
        self.NvAPI_Unload()

    @property
    def gpus(self) -> typing.List[NvPhysicalGpu]:
        if self.__gpus is None:
            gpus = NV_ENUM_GPUS()
            gpuCount = ctypes.c_int(-1)
            self.NvAPI_EnumPhysicalGPUs(gpus, ctypes.pointer(gpuCount))
            self.__gpus = [gpus[i] for i in range(gpuCount.value)]
        return self.__gpus


    def get_gpu_by_bus(self, busId: int, slotId: int) -> NvPhysicalGpu:
        for gpu in self.gpus:
            devBusId = ctypes.c_uint32(0)
            devSlotId = ctypes.c_uint32(0)
            self.NvAPI_GPU_GetBusId(gpu, ctypes.pointer(devBusId))
            self.NvAPI_GPU_GetBusSlotId(gpu, ctypes.pointer(devSlotId))

            if devBusId.value == busId and devSlotId.value == slotId:
                return gpu
        raise ValueError(f'Cannot find a GPU with bus={busId} and slot={slotId}')    

    def get_temps_ex(self, dev: NvPhysicalGpu, sensor_hint=None) -> typing.Tuple[int, typing.Tuple[float]]:
        exc = None
        counts = [sensor_hint] if sensor_hint is not None else range(32, 1, -1)
        for count in counts:
            thermal = NV_GPU_THERMAL_EX()
            thermal.mask = (1 << count) - 1
            try:
                self.NvAPI_GPU_GetAllTempsEx(dev, ctypes.pointer(thermal))
            except NvError as ex:
                exc = ex
                continue
            break
        else:
            raise exc
        return count, thermal.sensors

    def set_cooler_duty(self, dev: NvPhysicalGpu, cooler: int, duty: int):
        duty = max(min(duty, 100), 0)
        levels = NvCoolerLevels()
        for i in range(len(levels.levels)):
            levels.levels[i].level = duty
            levels.levels[i].policy = NVAPI_COOLER_POLICY_USER
        self.NvAPI_GPU_SetCoolerLevels(dev, cooler, ctypes.pointer(levels))

    def get_cooler_settings(self, dev: NvPhysicalGpu) -> NV_GPU_COOLER_SETTINGS:
        value = NV_GPU_COOLER_SETTINGS()
        self.NvAPI_GPU_GetCoolerSettings(dev, 0, ctypes.pointer(value))
        return value

    def get_freqs(self, dev: NvPhysicalGpu, type: int) -> NV_GPU_CLOCK_FREQUENCIES:
        value = NV_GPU_CLOCK_FREQUENCIES()
        value.ClockType = type
        self.NvAPI_GPU_GetAllClockFrequencies(dev, ctypes.pointer(value))
        return value

    def restore_coolers(self, dev: NvPhysicalGpu):
        self.NvAPI_GPU_RestoreCoolerSettings(dev, None, 0)

    def get_pstates(self, dev: NvPhysicalGpu) -> NV_GPU_PERF_PSTATES20_INFO:
        value = NV_GPU_PERF_PSTATES20_INFO()
        self.NvAPI_GPU_GetPstates20(dev, ctypes.pointer(value))
        return value

    def get_power_info(self, dev: NvPhysicalGpu) -> NV_GPU_POWER_INFO:
        value = NV_GPU_POWER_INFO()
        self.NvAPI_GPU_ClientPowerPoliciesGetInfo(dev, ctypes.pointer(value))
        return value
    
    def get_power_status(self, dev: NvPhysicalGpu) -> NV_GPU_POWER_STATUS:
        value = NV_GPU_POWER_STATUS()
        self.NvAPI_GPU_ClientPowerPoliciesGetStatus(dev, ctypes.pointer(value))
        return value

    def get_topology_status(self, dev: NvPhysicalGpu) -> NV_GPU_TOPOLOGY_STATUS:
        value = NV_GPU_TOPOLOGY_STATUS()
        self.NvAPI_GPU_ClientPowerTopologyGetStatus(dev, ctypes.pointer(value))
        return value
