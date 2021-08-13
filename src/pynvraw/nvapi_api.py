'''Low-level API working through obscure nvapi.dll.'''

import ctypes
import typing
import sys
import collections
import enum

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

NVAPI_MAX_GPU_TOPOLOGY_ENTRIES = 4

NvAPI_ShortString = ctypes.c_char * NVAPI_SHORT_STRING_MAX

class StrMixin:
    def __str__(self):
        dct = self.as_dict()
        result = [dct.pop('__name__') + ':']
        for k, v in dct.items():
            if isinstance(v, list):
                result.append(f'\t{k}=[')
                for e in v:
                    result.extend(f'\t\t{l}' for l in str(e).splitlines())
                result.append('\t]')
            elif isinstance(v, (dict, collections.OrderedDict, StrMixin)):
                v = str(v).splitlines()
                result.append(f'\t{k}={v[0]}')
                result.extend(f'\t{e}' for e in v[1:])
            else:
                result.append(f'\t{k}={v!s}')
        return '\n'.join(result)
    def __repr__(self):
        return self.__str__()
    @classmethod
    def _cast(cls, obj):
        if isinstance(obj, cls):
            return obj.as_dict()
        return str(obj)
    def as_dict(self):
        result = collections.OrderedDict(__name__=self.__class__.__name__)
        for fld in self._fields_:
            name = fld[0]
            if name.startswith('reserved'):
                continue
            if name.startswith('_') and hasattr(self, name[1:]):
                name = name[1:]
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, (list, tuple, ctypes.Array)):
                if len(value) == 0:
                    value = '[]'
                elif isinstance(value[0], (int, float, str, ctypes._SimpleCData)):
                    value = f'[{", ".join(map(str, value))}]'
                else:
                    value = [self._cast(e) for e in value]
            result[name] = value
        return result

class StrStructure(StrMixin, ctypes.Structure):
    pass

class StrUnion(StrMixin, ctypes.Union):
    pass

class NvPhysicalGpu(ctypes.Structure):
    _pack_ = 8
    _fields_ = [('unused', ctypes.c_int), 
                ('pad', ctypes.c_int8)]
NV_ENUM_GPUS = NvPhysicalGpu * NVAPI_MAX_PHYSICAL_GPUS

class NvVersioned(StrStructure):
    def __init__(self):
        self.version = ctypes.sizeof(self) + (self._nv_version_ << 16)

class NV_THERMAL_SENSOR(StrStructure):
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

class NV_COOLER_TARGET(enum.IntFlag):
    NONE = 0
    GPU = 1
    MEMORY = 2
    POWER_SUPPLY = 4
    ALL = 7    

class NvCoolerLevels(NvVersioned):
    class _NvCoolerLevel(StrStructure):
        _pack_ = 1
        _fields_ = [('level', ctypes.c_uint32),
                    ('policy', ctypes.c_uint32)]

    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('levels', _NvCoolerLevel * 20)]

class NV_GPU_COOLER_SETTINGS(NvVersioned):
    class NV_SINGLE_COOLER(StrStructure):
        _fields_ = [('type', ctypes.c_int32),
                    ('controller', ctypes.c_int32),
                    ('default_min', ctypes.c_int32),
                    ('default_max', ctypes.c_int32),
                    ('current_min', ctypes.c_int32),
                    ('current_max', ctypes.c_int32),
                    ('current_level', ctypes.c_int32),
                    ('default_policy', ctypes.c_int32),
                    ('current_policy', ctypes.c_int32),
                    ('_target', ctypes.c_int32),
                    ('control_type', ctypes.c_int32),
                    ('active', ctypes.c_int32)]
        @property
        def target(self):
            return NV_COOLER_TARGET(self._target)

    _nv_version_ = 2
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('coolers', NV_SINGLE_COOLER * 20)]

class NV_GPU_FAN_COOLERS_INFO(NvVersioned):
    class NV_GPU_FAN_COOLERS_INFO_ENTRY(StrStructure):
        _pack_ = 8
        _fields_ = [('coolerId', ctypes.c_uint32),
                    ('unknown', ctypes.c_uint32 * 2),
                    ('maxRpm', ctypes.c_uint32),
                    ('reserved', ctypes.c_uint32 * 8)]
    _nv_version_ = 1
    _pack_ = 8
    _fields_ = [('version', ctypes.c_uint32),
                ('supported', ctypes.c_bool),
                ('count', ctypes.c_uint32),
                ('reserved', ctypes.c_uint32 * 8),
                ('_entries', NV_GPU_FAN_COOLERS_INFO_ENTRY * 32)]

    @property
    def entries(self):
        return self._entries[:self.count]

class NV_GPU_FAN_COOLERS_STATUS(NvVersioned):
    class NV_GPU_FAN_COOLERS_STATUS_ENTRY(StrStructure):
        _pack_ = 8
        _fields_ = [('coolerId', ctypes.c_uint32),
                    ('currentRpm', ctypes.c_uint32),
                    ('minLevel', ctypes.c_uint32),
                    ('maxLevel', ctypes.c_uint32),
                    ('level', ctypes.c_uint32),
                    ('reserved', ctypes.c_uint32 * 8)]

    _nv_version_ = 1
    _pack_ = 8
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('reserved', ctypes.c_uint32 * 8),
                ('_entries', NV_GPU_FAN_COOLERS_STATUS_ENTRY * 32)]
    @property
    def entries(self):
        return self._entries[:self.count]

class FAN_COOLER_CONTROL_MODE(enum.IntEnum):
    AUTO = 0
    MANUAL = 1

class NV_GPU_FAN_COOLERS_CONTROL(NvVersioned):
    class NV_GPU_FAN_COOLERS_CONTROL_ENTRY(StrStructure):
        _pack_ = 8
        _fields_ = [('coolerId', ctypes.c_uint32),
                    ('level', ctypes.c_uint32),
                    ('_mode', ctypes.c_uint32),
                    ('reserved', ctypes.c_uint32 * 8)]
        @property
        def mode(self):
            return FAN_COOLER_CONTROL_MODE(self._mode)
        @mode.setter
        def mode(self, value):
            self._mode = int(value)

    _nv_version_ = 1
    _pack_ = 8
    _fields_ = [('version', ctypes.c_uint32),
                ('unknown', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('reserved', ctypes.c_uint32 * 8),
                ('_entries', NV_GPU_FAN_COOLERS_CONTROL_ENTRY * 32)]
    @property
    def entries(self):
        return self._entries[:self.count]

class NV_GPU_CLOCK_DOMAIN(StrStructure):
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

class NV_GPU_PERF_PSTATES20_PARAM_DELTA(StrStructure):
    _fields_ = [('value', ctypes.c_int32),
                ('valueMin', ctypes.c_int32),
                ('valueMax', ctypes.c_int32)]

class NV_GPU_PSTATE20_BASE_VOLTAGE_ENTRY_V1(StrStructure):
    _fields_ = [('domainId', ctypes.c_int),
                ('bIsEditable', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('volt_uV', ctypes.c_uint32),
                ('voltDelta_uV', NV_GPU_PERF_PSTATES20_PARAM_DELTA)]

class ClockType(enum.IntEnum):
    SINGLE = 0
    RANGE = 1

class NV_GPU_PUBLIC_CLOCK_ID(enum.IntEnum):
    GRAPHICS = 0
    MEMORY = 1
    PROCESSOR = 2
    VIDEO = 3
    MEMORY2 = 4
    UNDEFINED = 5

class NV_GPU_PERF_PSTATES20_INFO(NvVersioned):
    class _NV_GPU_PSTATE(StrStructure):
        def __init__(self):
            super().__init__()
            self.__numClocks = NVAPI_MAX_GPU_PSTATE20_CLOCKS
            self.__numVoltages = NVAPI_MAX_GPU_PSTATE20_BASE_VOLTAGES
        def _setNums(self, numClocks, numVoltages):
            self.__numClocks = numClocks
            self.__numVoltages = numVoltages

        class NV_GPU_PSTATE20_CLOCK_ENTRY_V1(StrStructure):
            class _NV_GPU_PSTATE_DATA_U(StrUnion):
                class _NV_GPU_PSTATE_DATA_RANGE(StrStructure):
                    _fields_ = [('_minFreq', ctypes.c_uint32),
                                ('_maxFreq', ctypes.c_uint32),
                                ('domainId', ctypes.c_int),
                                ('_minVoltage', ctypes.c_uint32),
                                ('_maxVoltage', ctypes.c_uint32)]
                    @property
                    def minFreq(self):
                        return self._minFreq / 1000.0
                    @property
                    def maxFreq(self):
                        return self._maxFreq / 1000.0
                    @property
                    def minVoltage(self):
                        return self._minVoltage / 1000000.0
                    @property
                    def maxVoltage(self):
                        return self._maxVoltage / 1000000.0

                _fields_ = [('_singleFreq', ctypes.c_uint32),
                            ('range', _NV_GPU_PSTATE_DATA_RANGE)]
                @property
                def singleFreq(self):
                    return self._singleFreq / 1000.0

            _fields_ = [('_domainId', ctypes.c_int),
                        ('_typeId', ctypes.c_int),
                        ('bIsEditable', ctypes.c_uint32, 1),
                        ('reserved', ctypes.c_uint32, 31),
                        ('freqDelta_kHz', NV_GPU_PERF_PSTATES20_PARAM_DELTA),
                        ('_data', _NV_GPU_PSTATE_DATA_U)]
            @property
            def domainId(self):
                return NV_GPU_PUBLIC_CLOCK_ID(self._domainId)
            @domainId.setter
            def domainId(self, value):
                self._domainId = int(value)
            @property
            def typeId(self):
                return ClockType(self._typeId)
            @property
            def data(self):
                attr = {ClockType.SINGLE: 'singleFreq',
                        ClockType.RANGE: 'range'}[self.typeId]
                return getattr(self._data, attr)

        _fields_ = [('pstateId', ctypes.c_int),
                    ('bIsEditable', ctypes.c_uint32, 1),
                    ('reserved', ctypes.c_uint32, 31),
                    ('_clocks', NV_GPU_PSTATE20_CLOCK_ENTRY_V1 * NVAPI_MAX_GPU_PSTATE20_CLOCKS),
                    ('_baseVoltages', NV_GPU_PSTATE20_BASE_VOLTAGE_ENTRY_V1 * NVAPI_MAX_GPU_PSTATE20_BASE_VOLTAGES)]
        @property
        def clocks(self):
            return self._clocks[:self.__numClocks]
        @property
        def baseVoltages(self):
            return self._baseVoltages[:self.__numVoltages]

    class _NV_GPU_OVERVOLT(StrStructure):
        _fields_ = [('numVoltages', ctypes.c_uint32),
                    ('_voltages', NV_GPU_PSTATE20_BASE_VOLTAGE_ENTRY_V1 * NVAPI_MAX_GPU_PSTATE20_BASE_VOLTAGES)]
        @property
        def voltages(self):
            return self._voltages[:self.numVoltages]

    _nv_version_ = 2
    _fields_ = [('version', ctypes.c_uint32),
                ('bIsEditable', ctypes.c_uint32, 1),
                ('reserved', ctypes.c_uint32, 31),
                ('numPstates', ctypes.c_uint32),
                ('numClocks', ctypes.c_uint32),
                ('numBaseVoltages', ctypes.c_uint32),
                ('_pstates', _NV_GPU_PSTATE * NVAPI_MAX_GPU_PSTATE20_PSTATES),
                ('ov', _NV_GPU_OVERVOLT)]
    @property
    def pstates(self):
        result = list(self._pstates[:self.numPstates])
        for p in result:
            p._setNums(self.numClocks, self.numBaseVoltages)
        return result

class _NV_GPU_POWER_INFO_ENTRY(StrStructure):
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

class _NV_GPU_POWER_STATUS_ENTRY(StrStructure):
    _fields_ = [('pad0', ctypes.c_uint32),
                ('pad1', ctypes.c_uint32),
                ('power', ctypes.c_uint32),
                ('pad2', ctypes.c_uint32)]

class NV_GPU_POWER_STATUS(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('entries', _NV_GPU_POWER_STATUS_ENTRY * 4)]

class NV_GPU_TOPOLOGY_ENTRY(StrStructure):
    _fields_ = [('domain', ctypes.c_int),
                ('reserved1', ctypes.c_int),
                ('_power', ctypes.c_uint32),
                ('reserved2', ctypes.c_int)]
    @property
    def power(self) -> float:
        return self._power / 1000.0

class NV_GPU_TOPOLOGY_STATUS(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('count', ctypes.c_uint32),
                ('entries', NV_GPU_TOPOLOGY_ENTRY * NVAPI_MAX_GPU_TOPOLOGY_ENTRIES)]

class PowerChannelType(enum.IntEnum):
    DEFAULT = 0
    SUMMATION = 1
    ESTIMATION = 2
    SLOW = 3
    GEMINI_CORRECTION = 4
    C1X = 5
    SENSOR = 6
    PSTATE_ESTIMATION_LUT = 7
    SENSOR_CLIENT_ALIGNED = 8

class PowerRailType(enum.IntEnum):
    UNKNOWN = 0
    OUT_NVVDD = 1
    OUT_FBVDD = 2
    OUT_FBVDDQ = 3
    OUT_FBVDD_Q = 4
    OUT_PEXVDD = 5
    OUT_A3V3 = 6
    OUT_3V3NV = 7
    OUT_TOTAL_GPU = 8
    OUT_FBVDDQ_GPU = 9
    OUT_FBVDDQ_MEM = 10
    OUT_SRAM = 11
    IN_PEX12V1 = 222
    IN_TOTAL_BOARD2 = 223
    IN_HIGH_VOLT0 = 224
    IN_HIGH_VOLT1 = 225
    IN_NVVDD1 = 226
    IN_NVVDD2 = 227
    IN_EXT12V_8PIN2 = 228
    IN_EXT12V_8PIN3 = 229
    IN_EXT12V_8PIN4 = 230
    IN_EXT12V_8PIN5 = 231
    IN_MISC0 = 232
    IN_MISC1 = 233
    IN_MISC2 = 234
    IN_MISC3 = 235
    IN_USBC0 = 236
    IN_USBC1 = 237
    IN_FAN0 = 238
    IN_FAN1 = 239
    IN_SRAM = 240
    IN_PWR_SRC_PP = 241
    IN_3V3_PP = 242
    IN_3V3_MAIN = 243
    IN_3V3_AON = 244
    IN_TOTAL_BOARD = 245
    IN_NVVDD = 246
    IN_FBVDD = 247
    IN_FBVDDQ = 248
    IN_FBVDD_Q = 249
    IN_EXT12V_8PIN0 = 250
    IN_EXT12V_8PIN1 = 251
    IN_EXT12V_6PIN0 = 252
    IN_EXT12V_6PIN1 = 253
    IN_PEX3V3 = 254
    IN_PEX12V = 255

class NV_POWER_MONITOR_INFO(NvVersioned):
    class NV_POWER_MONITOR_INFO_CHANNEL_INFO(StrStructure):
        class NV_POWER_MONITOR_INFO_CHANNEL_INFO_DATA(StrUnion):
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_1X_INFO(StrStructure):
                _fields_ = [('powerDeviceMask', ctypes.c_uint32),
                            ('powerLimit_mW', ctypes.c_uint32)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_SLOW_INFO(NV_GPU_POWER_MONITOR_POWER_CHANNEL_1X_INFO):
                pass
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_GEMINI_CORRECTION_INFO(NV_GPU_POWER_MONITOR_POWER_CHANNEL_SLOW_INFO):
                pass
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_SENSOR_INFO(StrStructure):
                _fields_ = [('powerDeviceIndex', ctypes.c_uint8),
                            ('powerDeviceProviderIndex', ctypes.c_uint8)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_SUMMATION_INFO(StrStructure):
                _fields_ = [('relationIndexFirst', ctypes.c_uint8),
                            ('relationIndexLast', ctypes.c_uint8)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_PSTATE_ESTIMATION_LUT_INFO(StrStructure):
                class NV_GPU_POWER_MONITOR_POWER_CHANNEL_PSTATE_ESTIMATION_LUT_ENTRY_INFO(StrStructure):
                    _fields_ = [('pstateId', ctypes.c_int32),
                                ('powerOffset', ctypes.c_uint32)]
                _fields_ = [('entries', NV_GPU_POWER_MONITOR_POWER_CHANNEL_PSTATE_ESTIMATION_LUT_ENTRY_INFO * 2)]
            _fields_ = [('c1x', NV_GPU_POWER_MONITOR_POWER_CHANNEL_1X_INFO),
                        ('gemmCorr', NV_GPU_POWER_MONITOR_POWER_CHANNEL_GEMINI_CORRECTION_INFO),
                        ('sensor', NV_GPU_POWER_MONITOR_POWER_CHANNEL_SENSOR_INFO),
                        ('slow', NV_GPU_POWER_MONITOR_POWER_CHANNEL_SLOW_INFO),
                        ('sum', NV_GPU_POWER_MONITOR_POWER_CHANNEL_SUMMATION_INFO),
                        ('pstateEstLUT', NV_GPU_POWER_MONITOR_POWER_CHANNEL_PSTATE_ESTIMATION_LUT_INFO),
                        ('reserved', ctypes.c_uint8 * 16)]

        _fields_ = [('deviceMask', ctypes.c_uint32),
                    ('_offset', ctypes.c_uint32),
                    ('_limit', ctypes.c_uint32),
                    ('_type', ctypes.c_uint32),
                    ('_rail', ctypes.c_uint32),
                    ('_voltFixed', ctypes.c_uint32),
                    ('powerCorrectSlope', ctypes.c_uint32),
                    ('currentCorrectSlope', ctypes.c_uint32),
                    ('currentOffset_mA', ctypes.c_int32),
                    ('reserved', ctypes.c_uint8 * 8),
                    ('_data', NV_POWER_MONITOR_INFO_CHANNEL_INFO_DATA)]
        TYPES = {
            PowerChannelType.SUMMATION: 'sum',
            PowerChannelType.SLOW: 'slow',
            PowerChannelType.GEMINI_CORRECTION: 'gemmCorr',
            PowerChannelType.C1X: 'c1x',
            PowerChannelType.SENSOR: 'sensor',
            PowerChannelType.PSTATE_ESTIMATION_LUT: 'pstateEstLUT',
        }

        @property
        def rail(self):
            return PowerRailType(self._rail)
        @property
        def type(self):
            return PowerChannelType(self._type)
        @property
        def data(self):
            attr = self.TYPES.get(self.type)
            if attr:
                return getattr(self._data, attr)
            return None
        @property
        def offset(self):
            '''Returns power offset in Watts.'''
            return self._offset / 1000.0
        @property
        def limit(self):
            '''Returns power limit in Watts.'''
            return self._limit / 1000.0
        @property
        def volt(self):
            '''Returns fixed voltage in Volts.'''
            return self._voltFixed / 1000.0

    class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_INFO(StrStructure):
        class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_INFO_DATA(StrUnion):
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_WEIGHT_INFO(StrStructure):
                _fields_ = [('weight', ctypes.c_int32)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_BALANCED_PHASE_EST_INFO(StrStructure):
                _fields_ = [('numTotalPhases', ctypes.c_uint8),
                            ('numStaticPhases', ctypes.c_uint8),
                            ('balancedPhasePolicyRelationIndexFirst', ctypes.c_uint8),
                            ('balancedPhasePolicyRelationIndexLast', ctypes.c_uint8)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_BALANCING_PWM_WEIGHT_INFO(StrStructure):
                _fields_ = [('balancingRelationIndex', ctypes.c_uint8),
                            ('bPrimary', ctypes.c_uint8)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_REGULATOR_LOSS_EST_INFO(StrStructure):
                _fields_ = [('regulatorType', ctypes.c_uint8),
                            ('coefficients', ctypes.c_int32 * 6)]
            class NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_REGULATOR_LOSS_DYN_INFO(StrStructure):
                _fields_ = [('thermMonIdx', ctypes.c_uint8),
                            ('voltDomain', ctypes.c_uint8)]
            _fields_ = [('weight', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_WEIGHT_INFO),
                        ('balancedPhaseEst', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_BALANCED_PHASE_EST_INFO),
                        ('balancingPwmWeight', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_BALANCING_PWM_WEIGHT_INFO),
                        ('regulatorLossEst', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_REGULATOR_LOSS_EST_INFO),
                        ('regulatorLossDyn', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_REGULATOR_LOSS_DYN_INFO),
                        ('reserved', ctypes.c_uint8 * 32)]
        _fields_ = [('_type', ctypes.c_int32),
                    ('channelIndex', ctypes.c_uint8),
                    ('_data', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_INFO_DATA)
                    ]
        TYPES = {0: ('WEIGHT', 'weight'),
                 1: ('BALANCED_PHASE_EST', 'balancedPhaseEst'),
                 2: ('BALANCING_PWM_WEIGHT', 'balancingPwmWeight'),
                 3: ('REGULATOR_LOSS_EST', 'regulatorLossEst'),
                 4: ('REGULATOR_LOSS_DYN', 'regulatorLossDyn'),
                 -1: ('UNKNOWN', None)}
        @property
        def type(self):
            return self.TYPES.get(self._type, [str(self._type)])[0]
        @property
        def data(self):
            attr = self.TYPES.get(self._type, [None, None])[1]
            if attr:
                return getattr(self._data, attr)
            return None

    _nv_version_ = 3
    #_pack_ = 4
    _fields_ = [('version', ctypes.c_uint32),
                ('isSupported', ctypes.c_bool),
                ('_samplingPeriod', ctypes.c_uint32),
                ('samplingCount', ctypes.c_uint32),
                ('channelMask', ctypes.c_uint32),
                ('channelRelationMask', ctypes.c_uint32),
                ('totalGpuPowerChannelMask', ctypes.c_uint32),
                ('totalGpuChannelIndex', ctypes.c_uint8),
                ('reserved', ctypes.c_uint8 * 8),
                ('channels', NV_POWER_MONITOR_INFO_CHANNEL_INFO * 32),
                ('relations', NV_GPU_POWER_MONITOR_POWER_CHANNEL_RELATIONSHIP_INFO * 32)]
    @property
    def samplingPeriod(self) -> float:
        '''Sampling period in seconds.'''
        return self._samplingPeriod / 1000.0

class NV_POWER_MONITOR_STATUS(NvVersioned):
    class NV_POWER_MONITOR_STATUS_ENTRY(StrStructure):
        _pack_ = 1
        _fields_ = [('_powerAvg', ctypes.c_uint32),
                    ('_powerMin', ctypes.c_uint32),
                    ('_powerMax', ctypes.c_uint32),
                    ('_current', ctypes.c_uint32),
                    ('_voltage', ctypes.c_uint32),
                    ('_energy', ctypes.c_uint64),
                    ('reserved', ctypes.c_uint8 * 16)]
        @property
        def power(self) -> float:
            '''Power consumption in Watts.'''
            return self._powerAvg / 1000.0
        @property
        def current(self):
            '''Current in Amperes.'''
            return self._current / 1000.0
        @property
        def voltage(self):
            '''Voltage in Volts.'''
            return self._voltage / 1000000.0

    _nv_version_ = 1
    # check: version == 0x1059C
    _fields_ = [('version', ctypes.c_uint32),
                ('channelMask', ctypes.c_uint32),
                ('_totalPower', ctypes.c_uint32),
                ('reserved', ctypes.c_uint8 * 16),
                ('entries', NV_POWER_MONITOR_STATUS_ENTRY * 32)]
    @property
    def totalPower(self) -> float:
        return self._totalPower / 1000.0

class NV_GPU_VOLTAGE_STATUS(NvVersioned):
    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('reserved1', ctypes.c_uint32),
                ('reserved2', ctypes.c_uint32 * 8),
                ('_voltage', ctypes.c_uint32),
                ('reserved3', ctypes.c_uint32 * 8)]
    @property
    def voltage(self):
        return self._voltage / 1000000.0

class NV_GPU_CLOCKBOOST_MASK(NvVersioned):
    class NV_GPU_CLOCKBOOST_MASK_CLOCK(StrStructure):
        _fields_ = [('_type', ctypes.c_uint32),
                    ('enabled', ctypes.c_bool),
                    ('reserved', ctypes.c_uint32 * 4)]
        @property
        def type(self):
            return NV_GPU_PUBLIC_CLOCK_ID(self._type)

    _nv_version_ = 1
    _pack_ = 8
    _fields_ = [('version', ctypes.c_uint32),
                ('masks', ctypes.c_uint32 * 16),
                ('clocks', NV_GPU_CLOCKBOOST_MASK_CLOCK * 255)]

class NV_GPU_CLOCKBOOST_TABLE(NvVersioned):
    class NV_GPU_CLOCKBOOST_TABLE_CLOCK(StrStructure):
        _fields_ = [('_type', ctypes.c_uint32),
                    ('reserved1', ctypes.c_uint32 * 4),
                    ('_freqDelta', ctypes.c_int32),
                    ('reserved2', ctypes.c_uint32 * 3)]
        @property
        def freqDelta(self):
            return self._freqDelta / 1000.0
        @property
        def type(self):
            return NV_GPU_PUBLIC_CLOCK_ID(self._type)

    _nv_version_ = 1
    _pack_ = 8
    _fields_ = [('version', ctypes.c_uint32),
                ('masks', ctypes.c_uint32 * 16),
                ('clocks', NV_GPU_CLOCKBOOST_TABLE_CLOCK * 255)]

class NV_GPU_VFP_CURVE(NvVersioned):
    class NV_GPU_VFP_CURVE_CLOCK(StrStructure):
        _fields_ = [('_type', ctypes.c_uint32),
                    ('_frequency', ctypes.c_uint32),
                    ('_voltage', ctypes.c_uint32),
                    ('reserved', ctypes.c_uint32 * 4)]
        @property
        def frequency(self):
            return self._frequency / 1000.0
        @property
        def voltage(self):
            return self._voltage / 1000000.0
        @property
        def type(self):
            return NV_GPU_PUBLIC_CLOCK_ID(self._type)

    _nv_version_ = 1
    _fields_ = [('version', ctypes.c_uint32),
                ('masks', ctypes.c_uint32 * 16),
                ('clocks', NV_GPU_VFP_CURVE_CLOCK * 255)]

class PerfCapReason(enum.IntFlag):
    NONE = 0
    POWER = 1
    TEMPERATURE = 2
    VOLTAGE = 4
    UNKNOWN = 8
    NO_LOAD = 16

class NV_GPU_PERFORMANCE_STATUS(NvVersioned):
    _nv_version_ = 1
    _pack_ = 8
    _fields_ = [('version', ctypes.c_uint32),
                ('unknown1', ctypes.c_uint32),
                ('_timer', ctypes.c_ulonglong),
                ('_limit', ctypes.c_uint32),
                ('unknown2', ctypes.c_uint32 * 3),
                ('_timers', ctypes.c_ulonglong * 3),
                ('unknown3', ctypes.c_uint32 * 326)]
    @property
    def timer(self):
        return self._timer / 1e9
    @property
    def limit(self):
        return PerfCapReason(self._limit)

class RamType(enum.IntEnum):
    Unknown = 0
    SDRAM = 1
    DDR1 = 2
    DDR2 = 3
    GDDR2 = 4
    GDDR3 = 5
    GDDR4 = 6
    DDR3 = 7
    GDDR5 = 8
    LPDDR2 = 9
    GDDR5X = 10
    HBM2 = 12
    GDDR6 = 14
    GDDR6X = 15

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
    NvAPI_SYS_GetDriverAndBranchVersion = NvMethod(0x2926AAAD, 'NvAPI_SYS_GetDriverAndBranchVersion', ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(NvAPI_ShortString))

    NvAPI_GPU_GetBusId = NvMethod(0x1BE0B8E5, 'NvAPI_GPU_GetBusId', NvPhysicalGpu, ctypes.POINTER(ctypes.c_uint32))
    NvAPI_GPU_GetBusSlotId = NvMethod(0x2A0A350F, 'NvAPI_GPU_GetBusSlotId', NvPhysicalGpu, ctypes.POINTER(ctypes.c_uint32))
    NvAPI_GPU_GetThermalSettings = NvMethod(0xE3640A56, 'NvAPI_GPU_GetThermalSettings', NvPhysicalGpu, ctypes.c_uint32, ctypes.POINTER(NV_GPU_THERMAL_SETTINGS))
    NvAPI_GPU_QueryThermalSensors  = NvMethod(0x65FE3AAD, 'NvAPI_GPU_QueryThermalSensors ', NvPhysicalGpu, ctypes.POINTER(NV_GPU_THERMAL_EX))
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
    NvAPI_GPU_PowerMonitorGetInfo = NvMethod(0xC12EB19E, 'NvAPI_GPU_PowerMonitorGetInfo', NvPhysicalGpu, ctypes.POINTER(NV_POWER_MONITOR_INFO))
    NvAPI_GPU_PowerMonitorGetStatus = NvMethod(0xF40238EF, 'NvAPI_GPU_PowerMonitorGetStatus', NvPhysicalGpu, ctypes.POINTER(NV_POWER_MONITOR_STATUS))

    NvAPI_GPU_ClientFanCoolersGetInfo = NvMethod(0xFB85B01E, 'NvAPI_GPU_ClientFanCoolersGetInfo', NvPhysicalGpu, ctypes.POINTER(NV_GPU_FAN_COOLERS_INFO))
    NvAPI_GPU_ClientFanCoolersGetStatus = NvMethod(0x35AED5E8, 'NvAPI_GPU_ClientFanCoolersGetStatus', NvPhysicalGpu, ctypes.POINTER(NV_GPU_FAN_COOLERS_STATUS))
    NvAPI_GPU_ClientFanCoolersGetControl = NvMethod(0x814B209F, 'NvAPI_GPU_ClientFanCoolersGetControl', NvPhysicalGpu, ctypes.POINTER(NV_GPU_FAN_COOLERS_CONTROL))
    NvAPI_GPU_ClientFanCoolersSetControl = NvMethod(0xA58971A5, 'NvAPI_GPU_ClientFanCoolersSetControl', NvPhysicalGpu, ctypes.POINTER(NV_GPU_FAN_COOLERS_CONTROL))

    NvAPI_GPU_GetCurrentVoltage = NvMethod(0x465F9BCF, 'NvAPI_GPU_GetCurrentVoltage', NvPhysicalGpu, ctypes.POINTER(NV_GPU_VOLTAGE_STATUS))

    NvAPI_GPU_GetClockBoostMask = NvMethod(0x507B4B59, 'NvAPI_GPU_GetClockBoostMask', NvPhysicalGpu, ctypes.POINTER(NV_GPU_CLOCKBOOST_MASK))
    NvAPI_GPU_GetVFPCurve = NvMethod(0x21537AD4, 'NvAPI_GPU_GetVFPCurve', NvPhysicalGpu, ctypes.POINTER(NV_GPU_VFP_CURVE))
    NvAPI_GPU_GetClockBoostTable = NvMethod(0x23F1B133, 'NvAPI_GPU_GetClockBoostTable', NvPhysicalGpu, ctypes.POINTER(NV_GPU_CLOCKBOOST_TABLE))
    NvAPI_GPU_SetClockBoostTable = NvMethod(0x733E009, 'NvAPI_GPU_SetClockBoostTable', NvPhysicalGpu, ctypes.POINTER(NV_GPU_CLOCKBOOST_TABLE))
    NvAPI_GPU_PerfPoliciesGetStatus = NvMethod(0x3D358A0C, 'NvAPI_GPU_PerfPoliciesGetStatus', NvPhysicalGpu, ctypes.POINTER(NV_GPU_PERFORMANCE_STATUS))

    NvAPI_GPU_GetRamType = NvMethod(0x57F7CAAC, 'NvAPI_GPU_GetRamType', NvPhysicalGpu, ctypes.POINTER(ctypes.c_uint32))

    def __init__(self):
        self.NvAPI_Initialize()
        self.__gpus = None

        version = ctypes.c_uint32(0)
        branch = NvAPI_ShortString()
        self.NvAPI_SYS_GetDriverAndBranchVersion(ctypes.pointer(version), branch)

        self.__version = version.value
        self.__branch = branch.value.decode('utf8')

        assert self.__version > 0x4650, f'Too old NVidia drivers (version={self.__version}, branch={self.__branch}): unsupported'

    def __del__(self):
        self.NvAPI_Unload()

    def get_driver_version(self) -> typing.Tuple[int, str]:
        '''Returns driver version as int and branch as str.'''
        return self.__version, self.__branch

    @property
    def gpu_handles(self) -> typing.List[NvPhysicalGpu]:
        if self.__gpus is None:
            gpus = NV_ENUM_GPUS()
            gpuCount = ctypes.c_int(-1)
            self.NvAPI_EnumPhysicalGPUs(gpus, ctypes.pointer(gpuCount))
            self.__gpus = [gpus[i] for i in range(gpuCount.value)]
        return self.__gpus


    def get_gpu_by_bus(self, busId: int, slotId: int) -> NvPhysicalGpu:
        for gpu in self.gpu_handles:
            devBusId = ctypes.c_uint32(0)
            devSlotId = ctypes.c_uint32(0)
            self.NvAPI_GPU_GetBusId(gpu, ctypes.pointer(devBusId))
            self.NvAPI_GPU_GetBusSlotId(gpu, ctypes.pointer(devSlotId))

            if devBusId.value == busId and devSlotId.value == slotId:
                return gpu
        raise ValueError(f'Cannot find a GPU with bus={busId} and slot={slotId}')    

    def read_thermal_sensors(self, dev: NvPhysicalGpu, sensor_hint=None) -> typing.Tuple[int, typing.Tuple[float]]:
        exc = None
        counts = [sensor_hint] if sensor_hint is not None else range(32, 1, -1)
        for count in counts:
            thermal = NV_GPU_THERMAL_EX()
            thermal.mask = (1 << count) - 1
            try:
                self.NvAPI_GPU_QueryThermalSensors (dev, ctypes.pointer(thermal))
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

    def get_cooler_settings(self, dev: NvPhysicalGpu, cooler: NV_COOLER_TARGET=NV_COOLER_TARGET.ALL) -> NV_GPU_COOLER_SETTINGS:
        value = NV_GPU_COOLER_SETTINGS()
        self.NvAPI_GPU_GetCoolerSettings(dev, int(cooler), ctypes.pointer(value))
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

    def get_power_monitor_info(self, dev: NvPhysicalGpu) -> NV_POWER_MONITOR_INFO:
        value = NV_POWER_MONITOR_INFO()
        self.NvAPI_GPU_PowerMonitorGetInfo(dev, ctypes.pointer(value))
        return value

    def get_power_monitor_status(self, dev: NvPhysicalGpu, info: NV_POWER_MONITOR_INFO) -> NV_POWER_MONITOR_STATUS:
        value = NV_POWER_MONITOR_STATUS()
        value.channelMask = info.channelMask
        self.NvAPI_GPU_PowerMonitorGetStatus(dev, ctypes.pointer(value))
        return value

    def get_coolers_info(self, dev: NvPhysicalGpu) -> NV_GPU_FAN_COOLERS_INFO:
        if self.__version < 0x9C40:
            raise ValueError('This feature requires new drivers')
        value = NV_GPU_FAN_COOLERS_INFO()
        self.NvAPI_GPU_ClientFanCoolersGetInfo(dev, ctypes.pointer(value))
        return value

    def get_coolers_status(self, dev: NvPhysicalGpu) -> NV_GPU_FAN_COOLERS_STATUS:
        if self.__version < 0x9C40:
            raise ValueError('This feature requires new drivers')
        value = NV_GPU_FAN_COOLERS_STATUS()
        self.NvAPI_GPU_ClientFanCoolersGetStatus(dev, ctypes.pointer(value))
        return value

    def get_coolers_control(self, dev: NvPhysicalGpu) -> NV_GPU_FAN_COOLERS_CONTROL:
        if self.__version < 0x9C40:
            raise ValueError('This feature requires new drivers')
        value = NV_GPU_FAN_COOLERS_CONTROL()
        self.NvAPI_GPU_ClientFanCoolersGetControl(dev, ctypes.pointer(value))
        return value

    def set_coolers_control(self, dev: NvPhysicalGpu, control: NV_GPU_FAN_COOLERS_CONTROL):
        if self.__version < 0x9C40:
            raise ValueError('This feature requires new drivers')
        self.NvAPI_GPU_ClientFanCoolersSetControl(dev, ctypes.pointer(control))

    def get_core_voltage(self, dev: NvPhysicalGpu) -> float:
        value = NV_GPU_VOLTAGE_STATUS()
        self.NvAPI_GPU_GetCurrentVoltage(dev, ctypes.pointer(value))
        return value.voltage

    def get_boost_mask(self, dev: NvPhysicalGpu) -> NV_GPU_CLOCKBOOST_MASK:
        value = NV_GPU_CLOCKBOOST_MASK()
        self.NvAPI_GPU_GetClockBoostMask(dev, ctypes.pointer(value))
        return value

    def get_boost_table(self, dev: NvPhysicalGpu, boost_mask: NV_GPU_CLOCKBOOST_MASK) -> NV_GPU_CLOCKBOOST_TABLE:
        value = NV_GPU_CLOCKBOOST_TABLE()
        for i, m in enumerate(boost_mask.masks):
            value.masks[i] = m
        self.NvAPI_GPU_GetClockBoostTable(dev, ctypes.pointer(value))
        return value

    def get_vfp_curve(self, dev: NvPhysicalGpu, boost_mask: NV_GPU_CLOCKBOOST_MASK) -> NV_GPU_VFP_CURVE:
        value = NV_GPU_VFP_CURVE()
        for i, m in enumerate(boost_mask.masks):
            value.masks[i] = m
        self.NvAPI_GPU_GetVFPCurve(dev, ctypes.pointer(value))
        return value

    def get_performance_limit(self, dev: NvPhysicalGpu) -> PerfCapReason:
        value = NV_GPU_PERFORMANCE_STATUS()
        self.NvAPI_GPU_PerfPoliciesGetStatus(dev, ctypes.pointer(value))
        return value.limit

    def get_ram_type(self, dev: NvPhysicalGpu) -> RamType:
        value = ctypes.c_uint32(0)
        self.NvAPI_GPU_GetRamType(dev, ctypes.pointer(value))
        return RamType(value.value)
