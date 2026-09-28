#!/usr/bin/env python3
"""直连正在运行的 Blender（走 MCP for Blender 插件的 socket 服务，默认 127.0.0.1:9876）。

为什么不用 MCP 协议：MCP 服务是会话启动时加载的，本会话里没有；
但插件本身就是一个 socket 服务，协议就三行——发 JSON、`handler(**params)`、回 JSON。
直连它就能在**开着视口的 Blender** 里跑任意 Python，
这是 headless 拿不到的能力（雕刻笔刷、mesh_filter、视口截图都要真视口）。

前置：Blender 里按 N → MCP for Blender 标签页 → Start MCP Server。

用法：
  python tools/blender-live.py info
  python tools/blender-live.py exec "import bpy; print(bpy.app.version_string)"
  python tools/blender-live.py shot out/preview.png
"""

from __future__ import annotations

import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 9876
TIMEOUT = 300.0


class BlenderNotReachable(RuntimeError):
    pass


def call(command: str, params: dict | None = None, *, timeout: float = TIMEOUT):
    payload = json.dumps({"type": command, "params": params or {}})
    try:
        with socket.create_connection((HOST, PORT), timeout=10.0) as sock:
            sock.settimeout(timeout)
            sock.sendall(payload.encode("utf-8"))
            chunks = []
            while True:
                try:
                    chunk = sock.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    return json.loads(b"".join(chunks).decode("utf-8"))
                except json.JSONDecodeError:
                    continue          # 消息可能被拆包，继续收
            raw = b"".join(chunks).decode("utf-8", "replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
    except (ConnectionRefusedError, OSError) as exc:
        raise BlenderNotReachable(
            f"连不上 Blender 的 socket 服务（{HOST}:{PORT}）：{exc}\n"
            "在 Blender 里按 N → 「MCP for Blender」标签页 → 点 Connect to MCP server"
            "（面板上应变成已连接 / 绿点）。"
        ) from exc


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2

    action = argv[0]
    try:
        if action == "info":
            result = call("get_scene_info")
        elif action == "exec":
            if len(argv) < 2:
                print("需要一段 Python 代码")
                return 2
            result = call("execute_code", {"code": argv[1]})
        elif action == "exec-file":
            if len(argv) < 2:
                print("需要一个脚本路径")
                return 2
            with open(argv[1], encoding="utf-8") as handle:
                result = call("execute_code", {"code": handle.read()}, timeout=600.0)
        elif action == "shot":
            result = call("get_viewport_screenshot", {"filepath": argv[1] if len(argv) > 1 else None})
        else:
            print(f"未知动作：{action}")
            return 2
    except BlenderNotReachable as exc:
        print(f"[blender-live] {exc}")
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
