from pynvraw import api, NvError, get_phys_gpu, nvapi_api

def main():
    print(api.get_driver_version())

    cuda_dev = 0
    while True:
        try:
            gpu = get_phys_gpu(cuda_dev)
        except ValueError:
            break
        print(f'{gpu.name}: core={gpu.core_temp} hotspot={gpu.hotspot_temp} vram={gpu.vram_temp}')
        print(f'{gpu.name}: fan={gpu.fan}%')

        '''
        try:
            v2 = api.get_coolers_info(gpu.handle)
        except NvError as ex:
            if ex.status == 'NVAPI_NOT_SUPPORTED':
                print(f'{gpu.name}: cooler_v2 api not supported')
            else:
                raise
        else:
            print(v2)
            print(api.get_coolers_status(gpu.handle))
            print(api.get_coolers_control(gpu.handle))
        '''

        #if '3090' in gpu.name:
        #    gpu.fan = 85

        for kind in 'base boost current'.split():
            print(f'clocks for {kind}: {gpu.get_freqs(kind)}')
        #try:
        #    api.restore_coolers(gpu.handle)
        #except NvError as err:
        #    if err.status != 'NVAPI_NOT_SUPPORTED':
        #        raise

        print(gpu.get_overclock())
        #gpu.set_overclock(nvapi.Clocks(core=-150, memory=200, processor=None, video=None))
        #gpu.fan = 50

        pinfo = api.get_power_info(gpu.handle)
        print(f'power info: valid={pinfo.valid} count={pinfo.count}')
        for entry in pinfo.entries[:pinfo.count]:
            print(f'\tpstate={entry.pstate}, min={entry.min_power/1000}%, def={entry.def_power/1000}%, max={entry.max_power/1000}%')
        pstates = api.get_pstates(gpu.handle)
        #print(pstates)
        print(f'Voltage: {api.get_core_voltage(gpu.handle)}V')
        #bmask = api.get_boost_mask(gpu.handle)
        #print(f'Boost mask:\n{bmask}')
        #print(f'Boost table:\n{api.get_boost_table(gpu.handle, bmask)}')

        #print(f'\t{pstates.ov.numVoltages=}')
        #for pstate in pstates.pstates[:pstates.numPstates]:
        #    print(f'\tstate={pstate.pstateId} edit={pstate.bIsEditable}')
        #    for bv in pstate.baseVoltages[:pstates.numBaseVoltages]:
        #        print(f'\t\tdomain={bv.domainId} edit={bv.bIsEditable} U={bv.volt_uV/1000000.:.4f}V (Umin={bv.voltDelta_uV.valueMin/1000000.:.4f}V | Ucur={bv.voltDelta_uV.value/1000000.:.4f}V | Umax={bv.voltDelta_uV.valueMax/1000000.:.4f}V')

        #for ov in pstates.ov.voltages[:pstates.ov.numVoltages]:
        #    print(f'\tdomain={ov.domain} edit={ov.bIsEditable} U={ov.volt_uV/1000000.:.4f}V (Umin={ov.voltDelta_uV.valueMin/1000000.:.4f}V | Ucur={ov.voltDelta_uV.value/1000000.:.4f}V | Umax={ov.voltDelta_uV.valueMax/1000000.:.4f}V')

        print(f'power limit: {gpu.power_limit}%')
        print(f'current power: {gpu.power}%')
        print(f'perf limit: {gpu.perf_limit!s}')

        '''
        mask = api.get_boost_mask(gpu.handle)
        vfp = api.get_vfp_curve(gpu.handle, mask)
        boost = api.get_boost_table(gpu.handle, mask)

        for idx, (mc, vc, bc) in enumerate(zip(mask.clocks, vfp.clocks, boost.clocks)):
            print(f'{idx=}\n{mc}\n{vc}\n{bc}')
        '''

        #gpu._show_boost_table()
        print(f'RAM type: {gpu.ram_type!s}')

        #powerInfo = api.get_power_monitor_info(gpu.handle)
        #print(powerInfo)
        #powerStatus = api.get_power_monitor_status(gpu.handle, powerInfo)
        #print(powerStatus)


        for rail, powers in gpu.get_rail_powers().items():
            if len(powers) > 1:
                print(f'{rail!s}:')
                for power in powers:
                    print(f'\tP={power.power:.2f}W I={power.current:.2f}A U={power.voltage:.2f}V')
            elif powers:
                print(f'{rail!s}: P={powers[0].power:.2f}W I={powers[0].current:.2f}A U={powers[0].voltage:.2f}V')
        
        #mon_info = api.get_power_monitor_info(gpu.handle)
        #mon_stat = api.get_power_monitor_status(gpu.handle, mon_info)
        #print(mon_info)
        #print(mon_stat)
        info = api.get_memory_info(gpu.handle)
        print(info)
        print(f'{gpu.memory_used=} MB / {gpu.memory_total=} MB')
        cuda_dev += 1

def main2():
    import pynvraw.nvapi_api as na
    for name in dir(na):
        if name == 'NvVersioned':
            continue
        obj = getattr(na, name)
        if isinstance(obj, type) and issubclass(obj, na.NvVersioned):
            print(f'{name}: version={hex(obj().version)}')

if __name__ == '__main__':
    main()
