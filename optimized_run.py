#!/usr/bin/env python3
"""
优化运行脚本：智能切换在线/离线模式
"""

import os
import sys
import argparse

def setup_environment(offline=False):
    """设置运行环境"""
    # 基本编码设置
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    if offline:
        # 离线模式：强制不从网络下载
        os.environ['HF_HUB_OFFLINE'] = '1'
        print("✓ 设置为离线模式")
    else:
        # 在线模式：使用国内镜像源
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        print("✓ 设置为在线模式（使用镜像源）")

def check_index_exists():
    """检查索引文件是否存在"""
    index_file = os.path.join('index', 'faiss_index.bin')
    meta_file = os.path.join('index', 'metadata.pkl')

    index_exists = os.path.exists(index_file)
    meta_exists = os.path.exists(meta_file)

    if index_exists and meta_exists:
        print(f"✓ 索引文件存在: {index_file}")
        print(f"✓ 元数据文件存在: {meta_file}")
        return True
    elif index_exists != meta_exists:
        print(f"⚠ 索引文件不完整:")
        print(f"  - faiss_index.bin: {'存在' if index_exists else '缺失'}")
        print(f"  - metadata.pkl: {'存在' if meta_exists else '缺失'}")
        print("  需要重新构建索引")
        return False
    else:
        print("✗ 索引文件不存在，需要先构建索引")
        return False

def check_model_cache():
    """检查模型是否在指定路径"""
    model_path = r"D:\向量数据库\all-MiniLM-L6-v2"

    if os.path.exists(model_path):
        print(f"✓ 本地模型存在: {model_path}")
        return True
    else:
        print(f"⚠ 本地模型不存在: {model_path}")
        return False

def run_build_mode():
    """运行构建模式"""
    print("\n" + "="*60)
    print("运行索引构建模式")
    print("="*60)

    # 构建模式需要在线下载模型
    setup_environment(offline=False)

    # 导入并运行main
    sys.argv = ['main.py', '--mode', 'build']
    exec(open('main.py', 'r', encoding='utf-8').read(), {'__name__': '__main__'})

def run_search_mode(query, offline=True):
    """运行搜索模式"""
    print("\n" + "="*60)
    print("运行搜索模式")
    print("="*60)
    print(f"查询: {query}")

    # 检查索引
    if not check_index_exists():
        print("\n请先构建索引:")
        print("  python optimized_run.py --mode build")
        return

    # 搜索模式可以离线
    setup_environment(offline=offline)

    # 导入并运行main
    sys.argv = ['main.py', '--mode', 'search', '--query', query]
    exec(open('main.py', 'r', encoding='utf-8').read(), {'__name__': '__main__'})

def run_interactive_mode(offline=True):
    """运行交互模式"""
    print("\n" + "="*60)
    print("运行交互式搜索模式")
    print("="*60)
    print("输入 'quit' 或 'exit' 退出")

    # 检查索引
    if not check_index_exists():
        print("\n请先构建索引:")
        print("  python optimized_run.py --mode build")
        return

    # 交互模式可以离线
    setup_environment(offline=offline)

    # 导入并运行main
    sys.argv = ['main.py', '--mode', 'interactive']
    exec(open('main.py', 'r', encoding='utf-8').read(), {'__name__': '__main__'})

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='优化版FAISS向量数据库系统')
    parser.add_argument('--mode', choices=['build', 'search', 'interactive'],
                       default='interactive', help='运行模式')
    parser.add_argument('--query', type=str, help='搜索查询（search模式使用）')
    parser.add_argument('--online', action='store_true',
                       help='强制在线模式（默认搜索时使用离线）')
    parser.add_argument('--offline', action='store_true',
                       help='强制离线模式')

    args = parser.parse_args()

    print("FAISS向量数据库优化版")
    print("="*60)

    # 检查模型缓存
    has_cache = check_model_cache()

    # 确定是否使用离线模式
    if args.offline:
        use_offline = True
    elif args.online:
        use_offline = False
    else:
        # 默认：构建模式在线，搜索模式离线
        use_offline = (args.mode != 'build')

    # 根据模式运行
    if args.mode == 'build':
        run_build_mode()
    elif args.mode == 'search':
        if not args.query:
            print("搜索模式需要提供查询")
            parser.print_help()
            return
        run_search_mode(args.query, offline=use_offline)
    else:  # interactive
        run_interactive_mode(offline=use_offline)

if __name__ == "__main__":
    # 设置控制台编码
    try:
        import subprocess
        subprocess.run(['chcp.com', '65001'], capture_output=True)
    except:
        pass

    main()