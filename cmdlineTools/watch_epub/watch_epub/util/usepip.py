#!/usr/bin/env python3
# coding: utf-8

# Reference:
# https://docs.python.org/3/installing/index.html
# https://packaging.python.org/tutorials/installing-packages/
# https://pip.pypa.io/en/stable/

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 7)
__all__ = [
    'check_pip', 'install_pip_by_ensurepip', 'install_pip_by_getpip', 
    'install_pip', 'execute_pip', 'execute_pip_in_child_process', 'install', 
    'uninstall', 'check_install', 'check_uninstall', 'ensure_import', 
]

import platform
import subprocess

from sys import executable
from tempfile import NamedTemporaryFile
from typing import Final, Iterable, List, Sequence, Union
from types import ModuleType
from urllib.parse import urlsplit
from urllib.request import urlopen


# When using subprocess.run on Windows, you should specify shell=True
_PLATFORM_IS_WINDOWS: Final[bool] = platform.system() == 'Windows'
## The following two may be redundant
# INDEX_URL: Base URL of the Python Package Index (default https://pypi.org/simple). 
#     This should point to a repository compliant with PEP 503 (the simple repository API)
#     or a local directory laid out in the same format.
INDEX_URL: str = 'https://mirrors.aliyun.com/pypi/simple/'
# TRUSTED_HOST: Mark this host or host:port pair as trusted,
#     even though it does not have valid or any HTTPS.
TRUSTED_HOST: str = 'mirrors.aliyun.com'


def _update_index_url(val: str):
    globals()['INDEX_URL'] = val
    install.__kwdefaults__['index_url'] = val # type: ignore
    split_result = urlsplit(val)
    if split_result.scheme == 'https':
        _update_trusted_host(split_result.netloc)


def _update_trusted_host(val: str):
    globals()['TRUSTED_HOST'] = val
    install.__kwdefaults__['trusted_host'] = val # type: ignore


if _PLATFORM_IS_WINDOWS:
    import site as _site
    from os import path as _path

    if not hasattr(_site, 'PREFIXES'):
        _site.PREFIXES = [__import__('sys').prefix, __import__('sys').exec_prefix]

    _site.ENABLE_USER_SITE = True

    _libpath = _path.dirname(_site.__file__)
    if not hasattr(_site, 'USER_BASE'):
        _site.USER_BASE = _path.dirname(_libpath)
    if not hasattr(_site, 'USER_SITE'):
        _site.USER_SITE = _path.join(_libpath, 'site-packages')

    del _site, _path, _libpath


def check_pip(ensure: bool = True) -> bool:
    'Check if the `pip` package is installed.'
    try:
        # Check whether the `pip` package can be imported
        import pip # type: ignore
    except ImportError:
        # If the `pip` package can't be imported, there may be reasons why it can't be installed
        try:
            ## Check configurations for `site-packages` 
            # USER_BASE: Path to the base directory for the user site-packages.
            # [site.USER_BASE](https://docs.python.org/3/library/site.html#site.USER_BASE)
            # USER_SITE: Path to the user site-packages for the running Python.
            # [site.USER_SITE](https://docs.python.org/3/library/site.html#site.USER_SITE)
            # NOTE: I found that the following file has a function `create_site_py`, `create_site_py` creates a site.py, 
            #       it is the actual imported `site` module in Windows platform, but there are lot of missing things: 
            # https://github.com/Sigil-Ebook/Sigil/blob/master/src/Resource_Files/python_pkg/windows_python_gather.py
            from site import USER_BASE, USER_SITE
            # TODO: I need to confirm whether the `site` built-in module exists in Windows platform, 
            #       if so, I can find out the values of `USER_BASE` and `USER_SITE` that are not missing, 
            #       otherwise, I may try to construct available values for `USER_BASE` and `USER_SITE`.
        except ImportError:
            print('''Defective Python executable detected.
Please replace current Python executable with another Python executable with `pip` package 
or replace with another Python executable which can install `pip` package 
(the `site` module defines available `USER_BASE` and `USER_SITE`).

Python official download address: https://www.python.org/downloads/

Tips: If you installed Python from source, with an installer from python.org, 
you should already have `pip`. If you installed using your OS package manager, 
`pip` may have been installed, or you can install separately by the same package manager.''')
            return False
        else:
            if not ensure:
                return False
            try:
                install_pip()
            except:
                return False
    return True


def install_pip_by_ensurepip(*args: str, new_process: bool = True) -> None:
    '''Install `pip` package using `ensurepip` package.
    Reference:
        - https://docs.python.org/3/library/ensurepip.html
        - https://packaging.python.org/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line
    '''
    if new_process:
        subprocess.run([executable, "-m", "ensurepip", *args], 
                       check=True, shell=_PLATFORM_IS_WINDOWS)
    else:
        from ensurepip import _main # type: ignore
        if not _main(list(args)):
            raise RuntimeError


def install_pip_by_getpip(
    *args: str, 
    check: bool = False,
    executable: str = executable,
) -> subprocess.CompletedProcess:
    '''Install `pip` package using bootstrapping script.
    Reference:
        - https://bootstrap.pypa.io/get-pip.py
        - https://packaging.python.org/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line
    '''
    with NamedTemporaryFile(mode='wb', suffix='.py') as f:
        f.write(b'''\
#!/usr/bin/env python
if platform.system() == 'Windows':
    import site as _site
    from os import path as _path

    if not hasattr(_site, 'PREFIXES'):
        _site.PREFIXES = [__import__('sys').prefix, __import__('sys').exec_prefix]

    _site.ENABLE_USER_SITE = True

    _libpath = _path.dirname(_site.__file__)
    if not hasattr(_site, 'USER_BASE'):
        _site.USER_BASE = _path.dirname(_libpath)
    if not hasattr(_site, 'USER_SITE'):
        _site.USER_SITE = _path.join(_libpath, 'site-packages')

    del _site, _path, _libpath
''')
        response = urlopen(
            'https://bootstrap.pypa.io/get-pip.py',
            context=__import__('ssl')._create_unverified_context()
        )
        f.write(response.read())
        f.flush()
        return subprocess.run([executable, f.name, *args], 
                              check=check, shell=_PLATFORM_IS_WINDOWS)


def install_pip(executable: str = executable) -> None:
    'Install `pip` package.'
    try:
        # https://docs.python.org/3/installing/index.html#pip-not-installed
        install_pip_by_ensurepip('--default-pip')
    except:
        args: List[str] = []
        index_url = globals().get('INDEX_URL')
        trusted_host = globals().get('TRUSTED_HOST')
        if index_url:
            args.extend(('-i', index_url))
            if not trusted_host:
                trusted_host = urlsplit(index_url).netloc
            if trusted_host:
                args.extend(('--trusted-host', trusted_host))

        install_pip_by_getpip(*args, check=True, executable=executable)


def execute_pip(args: Sequence[str]):
    'execute pip in same thread'
    from pip._internal import main
    return main(list(args))


def execute_pip_in_child_process(
    args: Union[str, Iterable[str]], 
    executable: str = executable, 
) -> subprocess.CompletedProcess:
    'execute pip in child process'
    command: Union[str, list]
    if isinstance(args, str):
        command = '"%s" -m pip %s' % (executable, args)
        return subprocess.run(command, shell=True)
    else:
        command = [executable, '-m', 'pip', *args]
        return subprocess.run(command, shell=_PLATFORM_IS_WINDOWS)


def install(
    package: str, 
    /, 
    *other_packages: str, 
    upgrade: bool = False, 
    index_url: str = INDEX_URL, 
    trusted_host: str = TRUSTED_HOST, 
    other_args: Iterable[str] = (), 
    new_process: bool = False, 
) -> None:
    'install package with pip'
    cmd = ['install']
    if index_url:
        cmd.extend(('-i', index_url))
        if not trusted_host:
            trusted_host = urlsplit(index_url).netloc
        if trusted_host:
            cmd.extend(('--trusted-host', trusted_host))
    if upgrade:
        cmd.append('--upgrade')
    cmd.extend(other_args)
    cmd.append(package)
    if other_packages:
        cmd.extend(other_packages)
    if new_process:
        execute_pip_in_child_process(cmd)
    else:
        execute_pip(cmd)


def uninstall(
    package: str, 
    /, 
    *other_packages: str,
    other_args: Iterable[str] = ('--yes',), 
    new_process: bool = False, 
) -> None:
    'uninstall package with pip'
    cmd = ['uninstall', *other_args, package, *other_packages]
    if new_process:
        execute_pip_in_child_process(cmd)
    else:
        execute_pip(cmd)


def check_install(
    module: str, 
    depencies: Union[None, str, Iterable[str]]= None,
) -> None:
    'Import the `module`, if it does not exist, try to install the `depencies`'
    try:
        __import__(module)
    except ModuleNotFoundError:
        if depencies is None:
            depencies = module,
        elif isinstance(depencies, str):
            depencies = depencies,
        install(*depencies)


def check_uninstall(
    module: str, 
    depencies: Union[None, str, Iterable[str]]= None,
) -> None:
    'Import the `module`, if it exists, try to uninstall the `depencies`'
    try:
        __import__(module)
        if depencies is None:
            depencies = module,
        elif isinstance(depencies, str):
            depencies = depencies,
        uninstall(*depencies)
    except ModuleNotFoundError:
        pass


def ensure_import(
    module: str, 
    depencies: Union[None, str, Iterable[str]]= None,
) -> ModuleType:
    '''Import the `module`, if it does not exist, try to install the `depencies`, 
    and then import it again.'''
    check_install(module, depencies)
    return __import__(module)


check_pip()

if __name__ == '__main__':
    execute_pip(__import__('sys').argv[1:])

