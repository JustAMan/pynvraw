from pynvraw import api, NvError, get_phys_gpu

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

        #if '3090' in gpu.name:
        #    gpu.fan = 85

        for kind in 'base boost current'.split():
            print(f'clocks for {kind}: {gpu.get_freqs(kind)}')
        try:
            api.restore_coolers(gpu.handle)
        except NvError as err:
            if err.status != 'NVAPI_NOT_SUPPORTED':
                raise

        print(gpu.get_overclock())
        #gpu.set_overclock(nvapi.Clocks(core=-150, memory=200, processor=None, video=None))
        #gpu.fan = 50

        pinfo = api.get_power_info(gpu.handle)
        print(f'power info: valid={pinfo.valid} count={pinfo.count}')
        for entry in pinfo.entries[:pinfo.count]:
            print(f'\tpstate={entry.pstate}, min={entry.min_power/1000}%, def={entry.def_power/1000}%, max={entry.max_power/1000}%')
        #pstates = api.get_pstates(gpu.handle)
        #print(pstates)
        #print(f'\t{pstates.ov.numVoltages=}')
        #for pstate in pstates.pstates[:pstates.numPstates]:
        #    print(f'\tstate={pstate.pstateId} edit={pstate.bIsEditable}')
        #    for bv in pstate.baseVoltages[:pstates.numBaseVoltages]:
        #        print(f'\t\tdomain={bv.domainId} edit={bv.bIsEditable} U={bv.volt_uV/1000000.:.4f}V (Umin={bv.voltDelta_uV.valueMin/1000000.:.4f}V | Ucur={bv.voltDelta_uV.value/1000000.:.4f}V | Umax={bv.voltDelta_uV.valueMax/1000000.:.4f}V')

        #for ov in pstates.ov.voltages[:pstates.ov.numVoltages]:
        #    print(f'\tdomain={ov.domain} edit={ov.bIsEditable} U={ov.volt_uV/1000000.:.4f}V (Umin={ov.voltDelta_uV.valueMin/1000000.:.4f}V | Ucur={ov.voltDelta_uV.value/1000000.:.4f}V | Umax={ov.voltDelta_uV.valueMax/1000000.:.4f}V')

        print(f'power limit: {gpu.power_limit}%')
        print(f'current power: {gpu.power}%')
        #gpu.set_power_limit(80)

        #powerInfo = api.get_power_monitor_info(gpu.handle)
        #print(powerInfo)
        #powerStatus = api.get_power_monitor_status(gpu.handle, powerInfo)
        #print(powerStatus)


        for rail, powers in gpu.get_rail_powers().items():
            for power in powers:
                print(f'{rail}: P={power.power:.2f}W I={power.current:.2f}A U={power.voltage:.2f}V')
        
        cuda_dev += 1

if __name__ == '__main__':
    main()
