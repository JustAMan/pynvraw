from pynvraw import api, NvError, get_phys_gpu

def main():
    cuda_dev = 0
    while True:
        try:
            gpu = get_phys_gpu(cuda_dev)
        except ValueError:
            break
        print(f'{gpu.name}: core={gpu.core_temp} hotspot={gpu.hotspot_temp} vram={gpu.vram_temp}')
        print(f'{gpu.name}: fan={gpu.fan}%')
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
        for idx in range(pinfo.count):
            entry = pinfo.entries[idx]
            print(f'\tpstate={entry.pstate}, min={entry.min_power/1000}%, def={entry.def_power/1000}%, max={entry.max_power/1000}%')

        print(f'power limit: {gpu.power_limit}%')
        print(f'current power: {gpu.power}%')
        #gpu.set_power_limit(80)

        for rail, powers in gpu.get_rail_powers().items():
            for power in powers:
                print(f'{rail}: P={power.power:.2f}W I={power.current:.2f}A U={power.voltage:.2f}V')
        
        cuda_dev += 1

if __name__ == '__main__':
    main()
