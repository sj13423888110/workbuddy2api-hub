# Windows 桌面启动器

给这个仓库加一个「双击就开」的桌面入口：端口在监听就直接开面板，没在监听就先拉起
`wb_proxy.py` 再开面板，全程无控制台窗口。

```
tools/windows-launcher/
├── launch.py          # 启动逻辑（用 pythonw.exe 执行，静默）
├── make_shortcut.py   # 创建带图标的 .lnk（调 IShellLink，不手写二进制）
├── gateway.ico        # 图标，9 个尺寸（256/128/64/48/40/32/24/20/16）
└── README.md
```

## 安装

```bat
cd /d <仓库路径>\tools\windows-launcher
python make_shortcut.py
```

它会在**真实桌面**（会被 OneDrive 重定向，脚本已按注册表取真实位置）创建
`WorkBuddy 网关.lnk`，目标是当前解释器同目录的 `pythonw.exe`，参数是本目录的
`launch.py`，图标用 `gateway.ico`。路径都是现算的，不含机器相关的硬编码。

自定义：

```bat
python make_shortcut.py --name "网关" --lnk "D:\x\网关.lnk"
python make_shortcut.py --target C:\Python313\pythonw.exe --args "C:\path\launch.py"
```

## 行为

| 场景 | 动作 |
|---|---|
| 端口已在监听 | 直接用默认浏览器打开面板，不重启网关 |
| 端口未监听 | 用 `pythonw` 以分离进程拉起 `wb_proxy.py --port 8788`，端口就绪后开面板 |
| 40 秒内没起来 | 弹窗提示 + 把原因写进日志 |

关网关请用面板顶栏的电源按钮（`POST /shutdown`），别关网页——两者是解耦的。

## 环境变量

| 变量 | 作用 |
|---|---|
| `WB_GW_REPO` | 显式指定仓库根（默认由脚本位置推：`tools/windows-launcher` 上两级） |
| `WB_GW_PORT` | 端口，默认 `8788` |
| `WB_GW_LOG` | 日志路径，默认 `%LOCALAPPDATA%\WorkBuddyGateway\launch.log` |
| `WB_GW_NOOPEN=1` | 只起网关，不开浏览器（便于测试） |

## 排错

先看 `%LOCALAPPDATA%\WorkBuddyGateway\launch.log`，每次启动都会记：

```
---- launcher start (pid 1234, exe ...pythonw.exe, repo ...)
spawning: ...pythonw.exe ...wb_proxy.py --port 8788
gateway ready after 4.7s
```

## 两个坑（踩过，写下来免得重犯）

1. **不要手写 `.lnk` 二进制。** 只写 `LinkInfo`、缺 `LinkTargetIDList` 的快捷方式
   Shell 不认：双击毫无反应，程序调用则报「没有应用程序与此操作的指定文件有关联」。
   `make_shortcut.py` 走系统 `IShellLink` + `IPersistFile`，IDList 由 Shell 自己生成。
2. **`.lnk` 的目标要是 `.exe`。** 指向 `.cmd` / `.bat` 的快捷方式同样执行不起来，
   所以入口做成了 `pythonw.exe` + 脚本参数，而不是快捷方式直接指向 bat。

顺带说一句：`.cmd` 这个类型没法单独换图标（图标由扩展名关联统一决定），
想在桌面上要自定义图标，就只能用 `.lnk` 承载。
