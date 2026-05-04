import asyncio
import inspect

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run test in an event loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if pyfuncitem.config.pluginmanager.hasplugin("asyncio"):
        return None

    test_function = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_function):
        return None

    kwargs = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
        if name in pyfuncitem.funcargs
    }
    asyncio.run(test_function(**kwargs))
    return True
