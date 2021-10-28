__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)


from json import load
from os import path
from runpy import run_path


def run(bc):
    prefs_path = path.join(bc._w.usrsupdir, 'plugins_prefs', 'runpyConfig', 'runpyConfig.json')
    try:
        prefs = load(open(prefs_path))
    except FileNotFoundError as exc:
        raise RuntimeError('请先运行 runpyConfig 插件配置脚本路径') from exc
    script_pathes = prefs['config']['path']
    for pth in script_pathes:
        run_path(pth, {'bc': bc, 'bk': bc})
    return 0

