#!/usr/bin/env python3
"""
运行构建脚本，确保环境变量正确设置
"""

import os
import sys
import subprocess

# 设置必要的环境变量
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

print("运行FAISS索引构建")
print("="*60)
print(f"工作目录: {os.getcwd()}")
print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT')}")
print(f"PYTHONUTF8: {os.environ.get('PYTHONUTF8')}")

# 检查配置文件
config_file = "config.json"
if os.path.exists(config_file):
    print(f"✓ 配置文件存在: {config_file}")
else:
    print(f"✗ 配置文件不存在: {config_file}")

# 检查数据目录
data_dir = "data"
if os.path.exists(data_dir):
    files = os.listdir(data_dir)
    print(f"✓ 数据目录存在: {data_dir} ({len(files)} 个文件)")
    for f in files:
        print(f"  - {f}")
else:
    print(f"✗ 数据目录不存在: {data_dir}")

# 直接导入并运行main模块
print("\n" + "="*60)
print("开始构建索引...")
print("="*60)

# 修改sys.argv来模拟命令行参数
sys.argv = ['main.py', '--mode', 'build']

# 导入main模块
try:
    # 首先测试模型加载
    print("\n1. 测试模型加载...")
    from sentence_transformers import SentenceTransformer
    model_name = "D:\\向量数据库\\all-MiniLM-L6-v2"

    print(f"   加载模型: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"   ✓ 模型加载成功，维度: {model.get_sentence_embedding_dimension()}")

    # 测试嵌入生成
    test_text = "这是一个测试句子"
    embedding = model.encode(test_text)
    print(f"   ✓ 嵌入生成成功，形状: {embedding.shape}")

except Exception as e:
    print(f"   ✗ 模型测试失败: {type(e).__name__}: {e}")
    print("\n尝试诊断问题...")

    # 检查网络连接
    import requests
    try:
        response = requests.get('https://hf-mirror.com', timeout=10)
        print(f"   网络连接测试: ✓ (状态码: {response.status_code})")
    except Exception as network_error:
        print(f"   网络连接测试: ✗ ({network_error})")

    sys.exit(1)

# 如果模型测试成功，运行完整的main函数
print("\n2. 运行完整的索引构建...")
try:
    # 执行main模块
    with open('main.py', 'r', encoding='utf-8') as f:
        exec(f.read(), {'__name__': '__main__'})
except SystemExit as e:
    print(f"\n程序退出代码: {e.code}")
except Exception as e:
    print(f"\n✗ 构建过程中出错: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("运行完成")
print("="*60)