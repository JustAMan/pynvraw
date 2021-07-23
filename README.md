# pynvraw
Pure-Python wrappings over `nvapi` which only require NVidia drivers and CUDA being isntalled on the machine.

Due to the nature of nvapi it only works on Windows (as nvapi is Windows-only).

This package allows monitoring of some values for NVidia cards and doing some basic control like setting fan rotation, power limit or overclock.

Use at your own risk!

# Inspirations
  - https://github.com/arrivan/fermtools/blob/master/nvapi/_NvAPI_IDs.txt
  - https://1vwjbxf1wko0yhnr.wordpress.com/2015/08/10/overclocking-tools-for-nvidia-gpus-suck-i-made-my-own/
  - https://github.com/falahati/NvAPIWrapper/blob/master/NvAPIWrapper/Native/Helpers/FunctionId.cs
  - https://github.com/graphitemaster/NVFC/blob/master/src/nvapi.cpp
  - https://github.com/processhacker/plugins-extra/blob/master/NvGpuPlugin/nvidia.h
  - https://github.com/processhacker/plugins-extra/blob/master/NvGpuPlugin/nvidia.c
  