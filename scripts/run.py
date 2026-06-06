#!/usr/bin/env python3
"""
启动脚本 - 自动管理虚拟环境和依赖
用法: python3 run.py <market> <code> <data_type>
示例:
  python3 run.py a 000001 quote
  python3 run.py hk 00700 technical
  python3 run.py us NVDA finance
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, ".venv")
REQUIREMENTS = os.path.join(SCRIPT_DIR, "requirements.txt")


def get_venv_python():
    """获取虚拟环境中的 python 路径"""
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")


def setup_venv():
    """创建虚拟环境并安装依赖"""
    venv_python = get_venv_python()

    if not os.path.exists(venv_python):
        print("首次运行，正在创建虚拟环境...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # 安装依赖
        print("正在安装依赖（httpx, pandas, akshare）...", file=sys.stderr)
        subprocess.check_call([venv_python, "-m", "pip", "install", "-r", REQUIREMENTS, "-q"],
                              stderr=subprocess.DEVNULL)
        print("依赖安装完成。", file=sys.stderr)

    return venv_python


def main():
    if len(sys.argv) < 4:
        print(f"""用法: python3 {sys.argv[0]} <market> <code> <data_type>

市场:
  a   - A股（腾讯/新浪API）
  hk  - 港股（腾讯/新浪API）
  us  - 美股（腾讯API）

数据类型:
  quote      - 实时行情
  finance    - 财务数据
  technical  - 技术面指标
  fund_flow  - 资金流向（A股/港股）
  valuation  - 估值数据
  all        - 全部数据

示例:
  python3 {sys.argv[0]} a 000001 quote
  python3 {sys.argv[0]} hk 00700 all
  python3 {sys.argv[0]} us NVDA finance
""", file=sys.stderr)
        sys.exit(1)

    market = sys.argv[1].lower()
    code = sys.argv[2]
    data_type = sys.argv[3]

    # 确定目标脚本
    script_map = {
        "a": "fetch_a_stock.py",
        "hk": "fetch_hk_stock.py",
        "us": "fetch_us_stock.py",
    }

    if market not in script_map:
        print(f"错误: 不支持的市场 '{market}'，支持: a, hk, us", file=sys.stderr)
        sys.exit(1)

    target_script = os.path.join(SCRIPT_DIR, script_map[market])

    # 确保虚拟环境就绪
    venv_python = setup_venv()

    # 在虚拟环境中运行目标脚本
    result = subprocess.run(
        [venv_python, target_script, code, data_type],
        capture_output=True, text=True
    )

    # 输出结果
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0 and result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
