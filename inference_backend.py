"""Own adapter for the original native extension, without its optional facade."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path

_handles=[]


def load():
    # Finding the top-level package does not execute its __init__.py.
    package=importlib.util.find_spec('upscale_ncnn_py')
    if package is None or not package.submodule_search_locations:
        raise RuntimeError('The original NCNN inference package is missing.')
    folder=Path(next(iter(package.submodule_search_locations)))
    _handles.append(os.add_dll_directory(str(folder)))
    name='upscale_ncnn_vulkan_wrapper'
    native=next((folder/(name+suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES
        if (folder/(name+suffix)).is_file()),None)
    if native is None:
        raise RuntimeError('No compatible original NCNN extension was found.')
    spec=importlib.util.spec_from_file_location(name,native)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
