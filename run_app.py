import os
import sys
import traceback
from multiprocessing import freeze_support

def main():
    # 获取当前可执行文件的绝对物理目录
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    # 强制将系统工作目录切换到 .exe 所在目录
    os.chdir(application_path)

    # 精确定位网页文件
    script_path = os.path.join(application_path, "airscience", "toweb_2.py")
    
    # 物理防呆检查：如果没有正确复制 airscience 文件夹，直接拦截并提示
    if not os.path.exists(script_path):
        print("\n" + "="*50)
        print(f"❌ 严重错误：找不到目标网页文件！\n预期路径: {script_path}")
        print("💡 请确认你已经把源码中的 'airscience' 文件夹粘贴到了 .exe 旁边！")
        print("="*50 + "\n")
        input("按回车键退出...")
        return

    print(f"✅ 成功找到网页文件: {script_path}")
    print("🚀 正在启动后台暖通计算大脑，请稍候，浏览器即将打开...")
    
    # 延迟导入 Streamlit，防止程序在启动初期就因依赖报错而瞬间闪退
    import streamlit.web.cli as stcli
    
    # 模拟命令行启动
    sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())

if __name__ == "__main__":
    # 核心修复：防止 Windows 下 PyInstaller 结合 Streamlit 发生多进程无限分叉崩溃
    freeze_support()
    
    try:
        main()
    except Exception as e:
        # 终极捕捉：如果发生任何意料之外的错误，写出到本地 txt 文件，并强制黑框停留
        error_file = "error_log_crash.txt"
        if getattr(sys, 'frozen', False):
            error_file = os.path.join(os.path.dirname(sys.executable), "error_log_crash.txt")
            
        with open(error_file, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
            
        print("\n" + "="*50)
        print("❌ 内部服务器启动失败！")
        print(f"详细报错代码已经写入到本地文件：{error_file}")
        print("你可以打开该 txt 文件查看，或将内容发给我分析。")
        print("="*50 + "\n")
        input("按回车键退出...")