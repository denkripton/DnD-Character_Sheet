import importlib

_LAZY_IMPORTS = {
    "register_exception_handlers": ("src.utils.exception_handlers", "register_exception_handlers"),
    "ErrorHandlingRoute": ("src.utils.routing.error_handling", "ErrorHandlingRoute"),
}

__all__ = ["ErrorHandlingRoute", "register_exception_handlers"]


def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'src.utils' has no attribute {name!r}")
    module_name, attr = _LAZY_IMPORTS[name]
    value = getattr(importlib.import_module(module_name), attr)
    globals()[name] = value
    return value