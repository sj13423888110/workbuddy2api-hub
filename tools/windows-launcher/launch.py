# -*- coding: utf-8 -*-
"""WorkBuddy 网关的 Windows 静默启动器。

用 pythonw.exe 执行（无控制台窗口）。行为：
  1. 端口已在监听 -> 直接打开面板
  2. 未监听 -> 用 pythonw 拉起 wb_proxy.py，等端口就绪后打开面板
  3. 起不来 -> 弹窗提示，并把细节写进日志

之所以要有这层壳而不是直接双击 .cmd：Windows 桌面快捷方式的目标必须是 .exe
才能稳定执行，指向 .cmd 的 .lnk 会双击无反应。

仓库位置默认由本文件位置推出（tools/windows-launcher/launch.py -> 仓库根），
也可以显式指定：
    set WB_GW_REPO=D:\\somewhere\\workbuddy2api-hub
    set WB_GW_PORT=8788
    set WB_GW_LOG=D:\\logs\\gateway-launch.log
    set WB_GW_NOOPEN=1        # 只起网关，不开浏览器
"""
import ctypes
import os
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("WB_GW_PORT", "8788"))
NO_OPEN = os.environ.get("WB_GW_NOOPEN") == "1"
URL = "http://127.0.0.1:%d/" % PORT

DETACHED = 0x00000008
NEW_GROUP = 0x00000200
NO_WINDOW = 0x08000000


def find_repo():
    explicit = os.environ.get("WB_GW_REPO")
    if explicit:
        return explicit
    # tools/windows-launcher -> 仓库根
    root = os.path.dirname(os.path.dirname(HERE))
    if os.path.isfile(os.path.join(root, "wb_proxy.py")):
        return root
    # 目录被单独拷出去用时，退回上一级
    root = os.path.dirname(HERE)
    if os.path.isfile(os.path.join(root, "wb_proxy.py")):
        return root
    return root


REPO = find_repo()
LOG = os.environ.get("WB_GW_LOG") or os.path.join(
    os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(),
    "WorkBuddyGateway", "launch.log",
)


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def alert(text):
    try:
        ctypes.windll.user32.MessageBoxW(None, text, "WorkBuddy 网关", 0x40)
    except Exception:
        pass


def listening(port=PORT, timeout=0.6):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def pythonw_path():
    """优先取当前解释器同目录的 pythonw.exe，避开 WindowsApps 里的商店别名。"""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for cand in (os.path.join(exe_dir, "pythonw.exe"),
                 os.path.join(exe_dir, "python.exe"),
                 sys.executable):
        if cand and os.path.isfile(cand) and "WindowsApps" not in cand:
            return cand
    return sys.executable


def open_panel():
    if NO_OPEN:
        log("WB_GW_NOOPEN=1, skip browser open")
        return
    webbrowser.open(URL)


def main():
    log("---- launcher start (pid %d, exe %s, repo %s)"
        % (os.getpid(), sys.executable, REPO))

    proxy = os.path.join(REPO, "wb_proxy.py")
    if not os.path.isfile(proxy):
        log("ERROR wb_proxy.py missing: %s" % proxy)
        alert("找不到网关程序：\n%s\n\n可用 WB_GW_REPO 环境变量指定仓库位置。" % proxy)
        return 1

    if listening():
        log("port %d already listening, just open dashboard" % PORT)
        open_panel()
        return 0

    exe = pythonw_path()
    cmd = [exe, proxy, "--port", str(PORT)]
    log("spawning: %s" % " ".join(cmd))
    try:
        subprocess.Popen(
            cmd,
            cwd=REPO,
            creationflags=DETACHED | NEW_GROUP | NO_WINDOW,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        log("ERROR spawn failed:\n" + traceback.format_exc())
        alert("启动网关失败，详情见：\n%s" % LOG)
        return 1

    deadline = time.time() + 40
    while time.time() < deadline:
        if listening():
            log("gateway ready after %.1fs" % (40 - (deadline - time.time())))
            time.sleep(0.3)
            open_panel()
            return 0
        time.sleep(0.8)

    log("ERROR port %d not listening within 40s" % PORT)
    alert("网关 40 秒内没有起来。\n可手动在终端里运行：\ncd /d %s\npython wb_proxy.py --port %d"
          % (REPO, PORT))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        alert("启动器异常，详情见：\n%s" % LOG)
        sys.exit(1)
