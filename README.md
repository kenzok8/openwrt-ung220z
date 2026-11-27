# openwrt-ung220z

UNG220Z 光猫凭据提取的 OpenWrt 插件。基于上游 [Hut-hzf/ung220z-tool](https://github.com/Hut-hzf/ung220z-tool)（MIT，vendored  commit `4eb1b1f7`，2026-11-22），只做一件事：在 LuCI 里点一下，拿到**你自己光猫**的 Web 超管、Telnet、PPPoE 宽带和 WiFi 密码。

> 仅用于你自己的设备：找回忘记的管理密码、迁移宽带配置、安全自查。未经授权对他人设备使用属于违法行为。

## 包含两个包

| 包 | 说明 |
|---|---|
| `ung220z-tool` | 后端：vendored 的 `ung220z.py`（纯标准库 Python），装到 `/usr/bin/ung220z`，可直接在命令行用 |
| `luci-app-ung220z` | 前端：LuCI 页面（服务 → UNG220Z）+ rpcd 服务，探测指纹、提取凭据、轮询结果 |

试点范围：**只做 UNG220Z（.gch 体系）+ 指纹探测**。上游 ontkit 的中兴 webFac、烽火、华为三路尚未接入——中兴那路要 `cryptography`（AES-ECB），OpenWrt 上得换成 `openssl enc`，等试点跑通再定。

## 依赖

- `ung220z-tool`：`python3-light` + `python3-urllib` + `openssl-util`
  - 注意 `urllib` 是独立包（`python3-urllib`），`python3-light` 不含它；`webbrowser` 也不含，已在 vendored 副本里做成可选导入。
  - root 口令比对调 `openssl passwd`，所以要 `openssl-util`。
- `luci-app-ung220z`：`ung220z-tool` + `luci-base` + `rpcd`

## 用法

LuCI → 服务 → UNG220Z：填光猫地址（默认 `192.168.1.1`）、用户名（默认 `user`）、背面贴纸密码 → 先点「探测」看指纹，再点「提取凭据」。

前提：**路由器必须能连上光猫**。光猫一般在 WAN 侧（桥接模式下通常是 192.168.1.1），路由器要有到它的路由，否则探测就报网关不可达。口令约每 15 分钟轮换一次（TR-069），重跑可取新值。

命令行：

```sh
# 只探测指纹
ung220z --json --probe -i 192.168.1.1

# 提取凭据（JSON 输出到 stdout，日志走 stderr，不落盘日志）
ung220z --json --no-browser -i 192.168.1.1 -u user --password-file /tmp/pw
```

退出码：0 成功 / 1 参数或异常 / 2 网关不可达 / 3 Telnet 端口未开 / 4 登录失败 / 5 配置解密失败 / 130 中断。

## 安全说明

- 密码不出现在进程列表里：LuCI 经 0600 临时文件传给后端，后端读完即删。
- JSON 模式不写日志文件（上游日志含明文凭据）；结果只在页面显示，不保存在路由器上，刷新即消失。
- 工具会在光猫上打开 Telnet 并留着，这是对设备的持久改动；解密出的明文配置在设备侧用完即删（上游 `finally` 里 `rm -f`）。
- rpcd 的 `extract` 只接受白名单字符的 IP/用户名；密码文件和任务目录均为 0600/0700。

## 上游同步

vendored 的 `ung220z.py` 与上游的差异只在 `[luci-patch]` 标注处（可选导入、`--json` / `--probe` / `--password-file`、失败出口 `_fail()`、汇总时多收 `telnet_users` 与 root 哈希）。差异以 unified diff 形式存在 `scripts/ung220z-luci.patch`，上游更新后：

```sh
bash scripts/sync-upstream.sh [<commit>]
```

脚本取上游指定 commit 的 `ung220z.py`，先 `--dry-run` 试打补丁：打不上就停下报 rejected hunks，人工 rebase，不强行打。打上后自动更新 vendored 副本并显示 diff。

**上游 bug（2026-11-27 核实）**：上游 `@4eb1b1f7` 的 `enable_telnet()` 签名没有 `timeout` 参数，但 `main()` 调用时传了 `timeout=a.timeout`，导致每次提取都在这里 `TypeError` 崩溃、退出码 1——上游原样跑不通提取。补丁里已顺手修掉（签名加 `timeout=8` 并传给 `http_get`）。同步上游时若该 bug 已在上游修掉，对应 hunk 会打不上，按提示人工处理；也可以给上游提 issue/ PR 报告。

## 状态

试点版 v1.0.0。mock 服务端到端验证通过（见 `scripts/mock-ont/`）：probe 指纹、不可达、telnet.gch 404、完整提取（含 root 口令比对）四条路。**未做真机验证**——需要一台 UNG220Z 或同款 .gch 光猫实测。
