import re
import numpy as np
from typing import Callable
from inspect import signature
from packaging import version
import socket
import random

import torch


def rerun_on_exception(exception_type: Exception = Exception, pattern: str = None, max_try: int = 5) -> Callable:
    """
    A decorator on a function to re-run when an exception occurs.

    Usage::

        # rerun for all kinds of exception
        @rerun_on_exception()
        def test_method():
            print('hey')
            raise RuntimeError('Address already in use')

        # rerun for RuntimeError only
        @rerun_on_exception(exception_type=RuntimeError)
        def test_method():
            print('hey')
            raise RuntimeError('Address already in use')

        # rerun for maximum 10 times if Runtime error occurs
        @rerun_on_exception(exception_type=RuntimeError, max_try=10)
        def test_method():
            print('hey')
            raise RuntimeError('Address already in use')

        # rerun for infinite times if Runtime error occurs
        @rerun_on_exception(exception_type=RuntimeError, max_try=None)
        def test_method():
            print('hey')
            raise RuntimeError('Address already in use')

        # rerun only the exception message is matched with pattern
        # for infinite times if Runtime error occurs
        @rerun_on_exception(exception_type=RuntimeError, pattern="^Address.*$")
        def test_method():
            print('hey')
            raise RuntimeError('Address already in use')

    Args:
        exception_type (Exception, Optional): The type of exception to detect for rerun
        pattern (str, Optional): The pattern to match the exception message.
            If the pattern is not None and matches the exception message,
            the exception will be detected for rerun
        max_try (int, Optional): Maximum reruns for this function. The default value is 5.
            If max_try is None, it will rerun foreven if exception keeps occurings
    """

    def _match_lines(lines, pattern):
        for line in lines:
            if re.match(pattern, line):
                return True
        return False

    def _wrapper(func):

        def _run_until_success(*args, **kwargs):
            try_count = 0
            assert max_try is None or isinstance(max_try, int), \
                f'Expected max_try to be None or int, but got {type(max_try)}'

            while max_try is None or try_count < max_try:
                try:
                    try_count += 1
                    ret = func(*args, **kwargs)
                    return ret
                except exception_type as e:
                    error_lines = str(e).split('\n')
                    if try_count < max_try and (pattern is None or _match_lines(error_lines, pattern)):
                        print('Exception is caught, retrying...')
                        # when pattern is not specified, we always skip the exception
                        # when pattern is specified, we only skip when pattern is matched
                        continue
                    else:
                        print('Maximum number of attempts is reached or pattern is not matched, no more retrying...')
                        raise e

        # Override signature
        # otherwise pytest.mark.parameterize will raise the following error:
        # function does not use argumetn xxx
        sig = signature(func)
        _run_until_success.__signature__ = sig

        return _run_until_success

    return _wrapper


def rerun_if_address_is_in_use():
    """
    This function reruns a wrapped function if "address already in use" occurs
    in testing spawned with torch.multiprocessing

    Usage::

        @rerun_if_address_is_in_use()
        def test_something():
            ...

    """
    # check version
    torch_version = version.parse(torch.__version__)
    assert torch_version.major == 1

    # only torch >= 1.8 has ProcessRaisedException
    if torch_version.minor >= 8:
        exception = torch.multiprocessing.ProcessRaisedException
    else:
        exception = Exception

    func_wrapper = rerun_on_exception(exception_type=exception, pattern=".*Address already in use.*")
    return func_wrapper


def free_port():
    while True:
        try:
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = random.randint(20000, 65000)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except Exception:
            continue


def synthesize_1d_sparse_feature(
    batch_size,
    num_embed,
    device,
):
    indices_in_batch = batch_size * 2
    indices = torch.randint(low=0, high=num_embed, size=(indices_in_batch,), device=device, dtype=torch.long)
    offsets = torch.from_numpy(
        np.array([
            0, *np.sort(np.random.randint(low=0, high=indices_in_batch, size=(indices_in_batch - 1,))), indices_in_batch
        ])).to(device).long()
    return indices, offsets
