import os
from sentence_transformers import SentenceTransformer

# 直接使用本地模型路径
model_dir = r'D:\向量数据库\all-MiniLM-L6-v2'

if os.path.exists(model_dir):
    print(f"✓ 找到本地模型: {model_dir}")
    model = SentenceTransformer(model_dir)
    print(f"✓ 模型加载成功，嵌入维度: {model.get_sentence_embedding_dimension()}")
else:
    print(f"✗ 找不到本地模型: {model_dir}")
    print("正在尝试下载模型...")
    from modelscope import snapshot_download
    model_dir = snapshot_download('sentence-transformers/all-MiniLM-L6-v2')
    print(f"✓ 模型已下载到: {model_dir}")