"""Functions to query GPUs in the system."""

import logging
import typing as t

from .errors import QueryError

_LOG = logging.getLogger(__name__)


try:

    try:
        import pycuda
        import pycuda.driver as cuda
    except ImportError as err:
        raise QueryError('unable to import pycuda') from err

    try:
        import pycuda.autoinit
    except pycuda._driver.Error as err:
        raise QueryError('') from err

    _LOG.debug('using CUDA version %s', '.'.join(str(_) for _ in cuda.get_version()))


    def query_gpus(**_) -> t.List[t.Mapping[str, t.Any]]:
        """Get information about all GPUs."""
        gpus = []
        for i in range(cuda.Device.count()):
            device = cuda.Device(i)
            gpus.append(query_gpu(device))
        return gpus


    def query_gpu(device: 'cuda.Device') -> t.Mapping[str, t.Any]:
        """Get information about a given GPU."""
        attributes = device.get_attributes()
        compute_capability = device.compute_capability()
        multiprocessors = attributes[cuda.device_attribute.MULTIPROCESSOR_COUNT]
        cuda_cores = calculate_cuda_cores(compute_capability, multiprocessors)
        try:
            return {
                'brand': device.name(),
                'memory': device.total_memory(),
                'memory_clock': attributes[cuda.device_attribute.MEMORY_CLOCK_RATE],
                'compute_capability': float('.'.join(str(_) for _ in compute_capability)),
                'clock': attributes[cuda.device_attribute.CLOCK_RATE],
                'multiprocessors': multiprocessors,
                'cores': cuda_cores,
                'warp_size': attributes[cuda.device_attribute.WARP_SIZE]
                }
        except KeyError as err:
            raise QueryError(
                'expected value not present among device attributes: {}'
                .format(device.get_attributes())) from err


except QueryError:

    _LOG.info('proceeding without GPU query support', exc_info=1)


    def query_gpus(**_) -> t.List[t.Mapping[str, t.Any]]:
        return []


def calculate_cuda_cores(compute_capability: t.Tuple[int, int], multiprocessors: int) -> int:
    """Calculate number of cuda cores according to Nvidia's specifications."""
    if compute_capability[0] == 2: # Fermi
        if compute_capability[1] == 1:
            return multiprocessors * 48
        return multiprocessors * 32
    elif compute_capability[0] == 3: # Kepler
        return multiprocessors * 192
    elif compute_capability[0] == 5: # Maxwell
        return multiprocessors * 128
    elif compute_capability[0] == 6: # Pascal
        if compute_capability[1] == 0:
            return multiprocessors * 64
        elif compute_capability[1] == 1:
            return multiprocessors * 128
        return None
    return None
