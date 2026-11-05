# 本仓库说明（个人修改版）

这是 [`ardeyouxipianyi/workbuddy2api-hub`](https://github.com/ardeyouxipianyi/workbuddy2api-hub) 的**个人修改版**，
在上游 `v1.10.9`（commit `077fb2f`）基础上增加了 6 个提交，全部改动只涉及看板体验、Codex 一键配置
与本机启动方式，没有改动账号池、代理出口、指纹处理等核心逻辑。

上游原项目为 MIT 协议，本仓库沿用。

---

## 与上游的差异

| 提交 | 内容 | 涉及文件 |
|---|---|---|
| `3616c1f` | 模型管理页新增「账号就绪」提示条：0 账号或账号全部不可用时点明"模型清单来自官方目录、不代表可调用"；顶部断连提示改为可操作（给出重启路径 + 一键重试） | `dashboard.html` |
| `095afcc` | 模型清单每行增加一键复制模型 ID 的图标按钮，供「添加自定义模型」直接粘贴 | `dashboard.html` |
| `caacf8e` | 登录弹窗「复制登录链接」右侧新增「扫码登录」，直接在新标签页打开当前授权链接（复用已有 `state`，不重新申请） | `dashboard.html` |
| `0ac332e` | 修 Codex 一键配置：`model_catalog_json` 指向自建目录，未选模型时丢弃 CC Switch 残留的非法模型名（如 `cn:auto`，上游返回 11102），改取目录首个真实 id；`restore` 一并回收自建目录 | `wb_agents.py` |
| `f0c6028` | 面板「保持登录」改由服务端持久化：勾选时 token 以 SHA-256 摘要落盘 `accounts/panel_sessions.json`，网关重启后免密（30 天）；不勾选仍只存内存 | `wb_settings.py`、`wb_proxy.py`、`dashboard.html` |
| `829fb8f` | 新增 Windows 桌面启动器 `tools/windows-launcher/`：`pythonw` 静默起网关并开面板（端口在监听则只开面板），`make_shortcut.py` 调 IShellLink 生成带图标的 `.lnk` | `tools/windows-launcher/` |

上游测试套件在改动后全部通过：`python tests/run_all.py` → **262 passed / 0 failed**。

---

## 在新机器上安装

### 方式一：git clone（推荐，便于以后拉上游更新）

```bash
git clone https://github.com/sj13423888110/workbuddy2api-hub.git
cd workbuddy2api-hub
python wb_proxy.py --port 8788
```

Windows 下也可以直接双击仓库里的 `start-wb-proxy.bat`（静默后台启动）。

### 桌面快捷方式（可选，Windows）

想要一个「双击就开面板、没在跑就先起服务」的桌面图标：

```bat
cd /d <仓库路径>\tools\windows-launcher
python make_shortcut.py
```

会在真实桌面生成 `WorkBuddy 网关.lnk`（图标为 `gateway.ico`）。目标写的是
`pythonw.exe` + `launch.py`，所以不会弹控制台窗口；路径都由脚本现算，不含机器相关的硬编码。
细节与排错见 `tools/windows-launcher/README.md`。

注意：`start-wb-proxy.bat` 和这个启动器功能重叠，**留一个就够**。两者都先查端口再决定是否拉起服务，
所以同时存在也不会起两个网关实例，只是没必要。

### 方式二：Download ZIP（机器上没有 git）

在仓库页面点 `Code` → `Download ZIP`，解压后同样用 `python wb_proxy.py --port 8788` 启动。

### 依赖

- **Python 3.9 及以上**，纯标准库，**不需要 pip 安装任何包**，没有 `requirements.txt`
- 首次启动后访问 `http://127.0.0.1:8788/`，面板默认密码 `admin`，**第一时间改掉**

### 加账号

面板「账号」页 →「+ 添加账号 (OAuth)」→ 用浏览器完成官方授权。账号文件会写到 `accounts/*.json`，
该目录已被 `.gitignore` 排除，不会进仓库。

---

## 拉取上游更新

本仓库保留了两个远程：

| 远程 | 地址 | 用途 |
|---|---|---|
| `origin` | 上游 `ardeyouxipianyi/workbuddy2api-hub` | 拉取上游新版本 |
| `mine` | 本仓库 | 推送自己的改动 |

```bash
git fetch origin
git merge origin/main      # 在本地分支上合并上游
git push mine HEAD:main    # 推回自己的仓库
```

改动集中在 `dashboard.html` 这一个文件的若干处，`wb_agents.py` / `wb_settings.py` / `wb_proxy.py` 各一处，
与上游冲突时按"保留上游新功能 + 重放这几处补丁"处理即可。

---

## 安全提醒

- `accounts/*.json`（账号凭据）、`usage/`（调用记录）、`logs/`、`catalog/*.json` 均被 `.gitignore` 排除
- 面板默认密码是 `admin`，开启"保持登录"后会话有效期 30 天。**部署在能被局域网访问的地址前，务必先改密码**
- 上游 README 顶部写明：2026-10-23 起上游收紧非官方客户端识别，风控/限流/封号由使用者自负。本仓库只是加了面板便利功能，不改变这一风险
