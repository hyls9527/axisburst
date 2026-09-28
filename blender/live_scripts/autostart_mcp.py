"""启动一个新的 Blender 实例并把 MCP socket 服务自动拉起来。

用途：当活动实例的通道被误断（比如脚本里用了 read_factory_settings），
不需要等人去界面点 Connect——新起一个实例自带服务即可。

用法：blender.exe --python <本文件>     （建议配合 -WindowStyle Hidden 启动）
"""
import addon_utils
import bpy


def main():
    try:
        addon_utils.enable("blender_mcp", default_set=False, persistent=True)
        print("AUTOSTART enable OK")
    except Exception as exc:  # noqa: BLE001
        print("AUTOSTART enable FAIL", type(exc).__name__, exc)

    if bpy.app.background:
        print("AUTOSTART 警告：background 实例没有视口，雕刻类操作不可用")

    try:
        result = bpy.ops.blendermcp.start_server()
        print("AUTOSTART start_server", result)
    except Exception as exc:  # noqa: BLE001
        print("AUTOSTART start FAIL", type(exc).__name__, exc)

    # 清掉默认场景件，给产品留干净的台面
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print("AUTOSTART ready, objects =", len(bpy.data.objects))


main()
