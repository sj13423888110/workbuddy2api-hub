# -*- coding: utf-8 -*-
"""创建带自定义图标的 Windows 快捷方式（.lnk）。

要点：不要手写 .lnk 二进制。缺 LinkTargetIDList 的 .lnk 会被 Shell 判为无效，
双击无反应、用程序调用则报"没有应用程序与此操作的指定文件有关联"。
这里直接调系统自带的 IShellLink / IPersistFile，由 Shell 自己写 IDList 与 LinkInfo。

用法（默认建桌面快捷方式，目标为本目录的 launch.py）：
    python make_shortcut.py
    python make_shortcut.py --lnk "D:\\x\\网关.lnk"
    python make_shortcut.py --name "网关" --icon ..\\windows-launcher\\gateway.ico

自定义目标：
    python make_shortcut.py --target C:\\Python313\\pythonw.exe \\
        --args "C:\\path\\launch.py" --workdir C:\\path\\repo
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import sys

CLSCTX_INPROC_SERVER = 1
ole32 = ctypes.oledll.ole32

CLSID_SHELLLINK = "{00021401-0000-0000-C000-000000000046}"
IID_ISHELLLINKW = "{000214F9-0000-0000-C000-000000000046}"
IID_IPERSISTFILE = "{0000010B-0000-0000-C000-000000000046}"

Vtbl = ctypes.POINTER(ctypes.c_void_p)


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, text):
        super().__init__()
        hr = ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(self))
        if hr != 0:
            raise OSError("CLSIDFromString failed 0x%08X for %s" % (hr & 0xFFFFFFFF, text))


def _fn(vtbl_ptr, index, restype, *argtypes):
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(vtbl_ptr[index])


def _check(hr, what):
    if hr & 0x80000000:
        raise OSError("%s failed 0x%08X" % (what, hr & 0xFFFFFFFF))


def make_shortcut(path, target, args="", workdir="", icon="", icon_index=0,
                  description="", show_cmd=1):
    """path=生成的 .lnk；target=可执行文件；args/workdir/icon 可为空。"""
    ole32.CoInitialize(None)
    try:
        clsid = GUID(CLSID_SHELLLINK)
        iid_link = GUID(IID_ISHELLLINKW)
        iid_persist = GUID(IID_IPERSISTFILE)

        punk = ctypes.c_void_p()
        _check(
            ole32.CoCreateInstance(ctypes.byref(clsid), None, CLSCTX_INPROC_SERVER,
                                   ctypes.byref(iid_link), ctypes.byref(punk)),
            "CoCreateInstance(ShellLink)",
        )

        vtbl = ctypes.cast(punk, ctypes.POINTER(Vtbl)).contents
        set_path = _fn(vtbl, 20, ctypes.HRESULT, wt.LPCWSTR)
        set_args = _fn(vtbl, 11, ctypes.HRESULT, wt.LPCWSTR)
        set_workdir = _fn(vtbl, 9, ctypes.HRESULT, wt.LPCWSTR)
        set_desc = _fn(vtbl, 7, ctypes.HRESULT, wt.LPCWSTR)
        set_icon = _fn(vtbl, 17, ctypes.HRESULT, wt.LPCWSTR, ctypes.c_int)
        set_show = _fn(vtbl, 15, ctypes.HRESULT, ctypes.c_int)
        query_iface = _fn(vtbl, 0, ctypes.HRESULT, ctypes.POINTER(GUID),
                          ctypes.POINTER(ctypes.c_void_p))

        _check(set_path(punk, target), "SetPath")
        if description:
            _check(set_desc(punk, description), "SetDescription")
        if args:
            _check(set_args(punk, args), "SetArguments")
        if workdir:
            _check(set_workdir(punk, workdir), "SetWorkingDirectory")
        if icon:
            _check(set_icon(punk, icon, icon_index), "SetIconLocation")
        _check(set_show(punk, show_cmd), "SetShowCmd")

        pfile = ctypes.c_void_p()
        _check(query_iface(punk, ctypes.byref(iid_persist), ctypes.byref(pfile)),
               "QueryInterface(IPersistFile)")
        pvtbl = ctypes.cast(pfile, ctypes.POINTER(Vtbl)).contents
        save = _fn(pvtbl, 6, ctypes.HRESULT, wt.LPCWSTR, wt.BOOL)
        _check(save(pfile, path, True), "IPersistFile.Save")

        _fn(pvtbl, 2, ctypes.c_ulong)(pfile)
        _fn(vtbl, 2, ctypes.c_ulong)(punk)
        return True
    finally:
        ole32.CoUninitialize()


def desktop_dir():
    """取真实桌面位置（可能被 OneDrive 重定向）。"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        val, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        val = os.path.expandvars(val)
        if os.path.isdir(val):
            return val
    except Exception:
        pass
    home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    for cand in (os.path.join(home, "OneDrive", "Desktop"), os.path.join(home, "Desktop")):
        if os.path.isdir(cand):
            return cand
    return os.path.join(home, "Desktop")


def pythonw_path():
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for cand in (os.path.join(exe_dir, "pythonw.exe"),
                 os.path.join(exe_dir, "python.exe"),
                 sys.executable):
        if cand and os.path.isfile(cand) and "WindowsApps" not in cand:
            return cand
    return sys.executable


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))

    ap = argparse.ArgumentParser(description="创建带图标的网关快捷方式")
    ap.add_argument("--lnk", help="生成的 .lnk 路径（默认：桌面/WorkBuddy 网关.lnk）")
    ap.add_argument("--name", default="WorkBuddy 网关", help="快捷方式显示名")
    ap.add_argument("--target", help="可执行目标（默认：pythonw.exe）")
    ap.add_argument("--args", help="目标参数（默认：本目录 launch.py）")
    ap.add_argument("--workdir", default=repo, help="工作目录（默认：仓库根）")
    ap.add_argument("--icon", default=os.path.join(here, "gateway.ico"), help="图标文件")
    ap.add_argument("--description", default="启动 WorkBuddy 网关并打开面板")
    args = ap.parse_args()

    lnk = args.lnk or os.path.join(desktop_dir(), args.name + ".lnk")
    target = args.target or pythonw_path()
    target_args = args.args if args.args is not None else '"%s"' % os.path.join(here, "launch.py")

    if not os.path.isfile(target):
        print("目标不存在：%s" % target, file=sys.stderr)
        return 2
    icon = args.icon if args.icon and os.path.isfile(args.icon) else ""

    make_shortcut(
        path=lnk, target=target, args=target_args, workdir=args.workdir,
        icon=icon, description=args.description,
    )
    print("已创建：%s (%d 字节)" % (lnk, os.path.getsize(lnk)))
    print("  目标：%s" % target)
    print("  参数：%s" % target_args)
    print("  图标：%s" % (icon or "(未设置)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
