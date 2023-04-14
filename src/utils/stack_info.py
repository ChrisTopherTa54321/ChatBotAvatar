import inspect
import os
from typing import Callable, List


def get_caller(exclude_func_prefixes: List[Callable] = []):
    exclude_func_prefixes = ['stack_info'] + exclude_func_prefixes
    stack_info = inspect.stack()
    for frame in stack_info:
        basename = os.path.basename(frame.filename)
        exclude_matches = [x for x in exclude_func_prefixes if basename.startswith(x)]
        if exclude_matches:
            continue
        break
    caller_info = f"{os.path.basename(frame.filename)}:{frame.lineno} {frame.function}"
    return caller_info
