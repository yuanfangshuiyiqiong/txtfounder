#!/usr/bin/env python3
"""
FAISS向量数据库操作手册存储与搜索系统

功能：
1. 支持多种文档格式：txt、pdf、docx、md
2. 文本分块处理
3. 使用多种嵌入模型：本地sentence-transformers或OpenAI API
4. 构建FAISS向量索引并保存
5. 支持相似度搜索和关键词搜索

使用说明：
1. 安装依赖：pip install -r requirements.txt
2. 准备操作手册文件
3. 运行脚本进行索引构建和搜索

配置说明：
- 修改config部分设置文件路径、模型参数等
"""

import os
import sys
import json
import pickle
import argparse
import logging
import sqlite3
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# 第三方库导入（需要先安装）
try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    # 尝试两种导入方式，支持不同版本的langchain
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    import PyPDF2
    from docx import Document
    import pandas as pd
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请先安装所需依赖：")
    print("pip install numpy faiss-cpu sentence-transformers langchain pypdf2 python-docx pandas openpyxl")
    print("对于较新的langchain版本，可能还需要：pip install langchain-text-splitters")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置文件
class Config:
    """配置类"""
    # 文件路径配置
    DATA_DIR = "data"  # 操作手册文件目录
    INDEX_DIR = "index"  # 索引保存目录
    INDEX_FILE = "faiss_index.bin"  # FAISS索引文件名
    META_FILE = "metadata.pkl"  # 元数据文件名
    DB_FILE = "documents.db"  # 数据库文件名

    # 文本处理配置
    CHUNK_SIZE = 500  # 文本块大小（字符数）
    CHUNK_OVERLAP = 50  # 文本块重叠大小

    # 嵌入模型配置
    EMBEDDING_MODEL = "D:\\liworkplace\\APQP faiss database\\向量数据库 - 副本\\all-MiniLM-L6-v2"  # 本地模型路径
    EMBEDDING_DIM = 384  # 嵌入向量维度（all-MiniLM-L6-v2的维度）

    # 搜索配置
    TOP_K = 5  # 返回最相似的结果数量

    @classmethod
    def ensure_dirs(cls):
        """确保必要的目录存在"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.INDEX_DIR, exist_ok=True)

    @classmethod
    def get_index_path(cls):
        """获取索引文件路径"""
        return os.path.join(cls.INDEX_DIR, cls.INDEX_FILE)

    @classmethod
    def get_meta_path(cls):
        """获取元数据文件路径"""
        return os.path.join(cls.INDEX_DIR, cls.META_FILE)

    @classmethod
    def get_db_path(cls):
        """获取数据库文件路径"""
        return os.path.join(cls.INDEX_DIR, cls.DB_FILE)


class DatabaseManager:
    """数据库管理器，负责持久化存储文档和元数据"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 创建文档块表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    file_name TEXT,
                    file_path TEXT,
                    chunk_index INTEGER,
                    content TEXT,
                    metadata TEXT
                )
            ''')
            # 创建已处理文件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_path TEXT PRIMARY KEY,
                    last_modified REAL
                )
            ''')
            conn.commit()

    def save_chunks(self, chunks: List[Dict[str, Any]], overwrite: bool = True):
        """批量保存文档块"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if overwrite:
                cursor.execute("DELETE FROM document_chunks")
            
            data = []
            for chunk in chunks:
                data.append((
                    chunk['id'],
                    chunk['file_name'],
                    chunk['file_path'],
                    chunk['chunk_index'],
                    chunk['content'],
                    json.dumps(chunk.get('metadata', {}), ensure_ascii=False)
                ))
            
            cursor.executemany('''
                INSERT INTO document_chunks (id, file_name, file_path, chunk_index, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
            logger.info(f"已将 {len(chunks)} 个文本块保存到数据库: {self.db_path}")

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文本块"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_chunks WHERE id = ?", (chunk_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def load_all_chunks(self) -> List[Dict[str, Any]]:
        """加载所有文本块"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_chunks ORDER BY file_path, chunk_index")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_processed_files(self) -> Dict[str, float]:
        """获取已处理文件的记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path, last_modified FROM processed_files")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def update_processed_files(self, file_paths: List[str]):
        """更新已处理文件记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for file_path in file_paths:
                last_modified = os.path.getmtime(file_path)
                cursor.execute("INSERT OR REPLACE INTO processed_files (file_path, last_modified) VALUES (?, ?)",
                               (file_path, last_modified))
            conn.commit()

    def remove_chunks_by_file_path(self, file_path: str):
        """根据文件路径删除文本块"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM document_chunks WHERE file_path = ?", (file_path,))
            conn.commit()


class DocumentLoader:
    """文档加载器，支持多种格式"""

    @staticmethod
    def load_text_file(file_path: str) -> str:
        """加载文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()

    @staticmethod
    def load_pdf_file(file_path: str) -> str:
        """加载PDF文件"""
        text = ""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"加载PDF文件失败 {file_path}: {e}")
        return text

    @staticmethod
    def load_docx_file(file_path: str) -> str:
        """加载Word文档"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"加载Word文档失败 {file_path}: {e}")
        return text

    @staticmethod
    def load_excel_file(file_path: str) -> str:
        """加载Excel文件"""
        text = ""
        try:
            # 首先尝试使用 calamine 引擎，它更稳健
            try:
                excel_data = pd.read_excel(file_path, sheet_name=None, engine='calamine')
            except Exception:
                # 降级使用默认引擎
                excel_data = pd.read_excel(file_path, sheet_name=None)
            
            for sheet_name, df in excel_data.items():
                text += f"工作表: {sheet_name}\n"
                # 将表格转换为字符串，处理空值
                text += df.to_string(index=False, na_rep='') + "\n\n"
        except Exception as e:
            error_msg = str(e)
            if "defaultColWidthPt" in error_msg:
                logger.error(f"加载Excel文件失败 {file_path}: 该文件格式较新，当前的 openpyxl 库存在兼容性问题。")
                logger.error("解决办法：请将该 Excel 文件重新‘另存为’一次标准的 .xlsx 格式，或升级环境中的 openpyxl 库。")
            else:
                logger.error(f"加载Excel文件失败 {file_path}: {e}")
        return text

    @classmethod
    def load_document(cls, file_path: str) -> Optional[str]:
        """根据文件扩展名加载文档"""
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.txt':
            return cls.load_text_file(file_path)
        elif file_ext == '.pdf':
            return cls.load_pdf_file(file_path)
        elif file_ext in ['.docx', '.doc']:
            return cls.load_docx_file(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            return cls.load_excel_file(file_path)
        elif file_ext == '.md':
            return cls.load_text_file(file_path)
        else:
            logger.warning(f"不支持的文件格式: {file_ext}")
            return None

    @classmethod
    def load_all_documents(cls, data_dir: str, processed_files: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """加载目录中的所有新文档或已修改的文档"""
        documents = []
        if processed_files is None:
            processed_files = {}

        if not os.path.exists(data_dir):
            logger.error(f"数据目录不存在: {data_dir}")
            return documents

        for root, _, files in os.walk(data_dir):
            for file in files:
                # 忽略 Office 临时文件（以 ~$ 开头）
                if file.startswith('~$'):
                    continue

                file_path = os.path.join(root, file)
                last_modified = os.path.getmtime(file_path)

                # 检查文件是否需要更新
                if file_path in processed_files and last_modified <= processed_files[file_path]:
                    continue  # 文件未修改，跳过

                content = cls.load_document(file_path)

                if content:
                    rel_path = os.path.relpath(file_path, data_dir)
                    documents.append({
                        'file_path': rel_path,
                        'full_path': file_path,
                        'content': content,
                        'file_name': file
                    })
                    logger.info(f"加载新/已修改文档: {rel_path} ({len(content)} 字符)")

        return documents


class TextProcessor:
    """文本处理器"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )

    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将文档分割成小块"""
        chunks = []

        for doc in documents:
            content = doc['content']
            file_path = doc['file_path']
            file_name = doc['file_name']

            # 分割文本
            text_chunks = self.text_splitter.split_text(content)

            for i, chunk in enumerate(text_chunks):
                chunk_id = f"{file_path}_chunk_{i}"
                chunks.append({
                    'id': chunk_id,
                    'file_path': file_path,
                    'file_name': file_name,
                    'chunk_index': i,
                    'content': chunk,
                    'original_doc': doc
                })

        logger.info(f"将 {len(documents)} 个文档分割成 {len(chunks)} 个文本块")
        return chunks


class EmbeddingGenerator:
    """嵌入向量生成器"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.embedding_dim = None

        # 加载本地模型
        try:
            logger.info(f"加载本地嵌入模型: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"模型加载完成，嵌入维度: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"加载本地模型失败: {e}")
            raise

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """生成嵌入向量"""
        if not texts:
            return np.array([])

        embeddings = self.model.encode(texts, show_progress_bar=True)
        return np.array(embeddings).astype('float32')


class FAISSIndex:
    """FAISS索引管理器"""

    def __init__(self, embedding_dim: int):
        self.embedding_dim = embedding_dim
        self.index = None
        self.metadata = []

    def build_index(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """构建FAISS索引"""
        if len(embeddings) == 0:
            raise ValueError("没有嵌入向量可以构建索引")

        # 创建索引（使用内积相似度，相当于余弦相似度，因为向量已归一化）
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        # 归一化向量（使余弦相似度计算更准确）
        faiss.normalize_L2(embeddings)

        # 添加向量到索引
        self.index.add(embeddings)
        self.metadata = metadata

        logger.info(f"构建FAISS索引完成，包含 {len(embeddings)} 个向量")

    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """向现有索引中添加新数据"""
        if self.index is None:
            raise ValueError("索引尚未构建，无法添加数据")
        if len(embeddings) == 0:
            return

        # 归一化新向量
        faiss.normalize_L2(embeddings)

        # 添加到索引
        self.index.add(embeddings)
        self.metadata.extend(metadata)

        logger.info(f"向FAISS索引中添加了 {len(embeddings)} 个新向量")

    def save_index(self, index_path: str, meta_path: str) -> None:
        """保存索引和元数据"""
        if self.index is None:
            raise ValueError("索引尚未构建")

        # 保存FAISS索引
        faiss.write_index(self.index, index_path)

        # 保存元数据
        with open(meta_path, 'wb') as f:
            pickle.dump(self.metadata, f)

        logger.info(f"索引已保存: {index_path}")
        logger.info(f"元数据已保存: {meta_path}")

    def load_index(self, index_path: str, meta_path: str) -> None:
        """加载索引和元数据"""
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"索引文件不存在: {index_path}")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"元数据文件不存在: {meta_path}")

        # 加载FAISS索引
        self.index = faiss.read_index(index_path)

        # 加载元数据
        with open(meta_path, 'rb') as f:
            self.metadata = pickle.load(f)

        logger.info(f"索引已加载: {index_path}")
        logger.info(f"元数据已加载: {meta_path}")
        logger.info(f"索引包含 {self.index.ntotal} 个向量")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        if self.index is None:
            raise ValueError("索引尚未加载或构建")

        # 归一化查询向量
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        # 搜索
        distances, indices = self.index.search(query_embedding, top_k)

        # 构建结果
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx >= 0 and idx < len(self.metadata):  # 有效索引
                distance = distances[0][i]
                metadata = self.metadata[idx]

                # 将距离转换为相似度分数（0-1范围）
                similarity_score = (distance + 1) / 2  # 从[-1,1]映射到[0,1]

                results.append({
                    'rank': i + 1,
                    'similarity_score': similarity_score,
                    'distance': distance,
                    'content': metadata.get('content', ''),
                    'file_path': metadata.get('file_path', ''),
                    'file_name': metadata.get('file_name', ''),
                    'chunk_index': metadata.get('chunk_index', -1),
                    'metadata': metadata
                })

        return results


class ManualSearchSystem:
    """操作手册搜索系统"""

    def __init__(self, config: Config):
        self.config = config
        self.document_loader = DocumentLoader()
        self.text_processor = TextProcessor(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        self.db_manager = None
        self.embedding_generator = None
        self.faiss_index = None
        self.is_initialized = False

    def initialize(self) -> None:
        """初始化系统"""
        logger.info("初始化操作手册搜索系统...")

        # 确保目录存在
        self.config.ensure_dirs()

        # 初始化数据库管理器
        self.db_manager = DatabaseManager(self.config.get_db_path())

        # 初始化嵌入生成器
        self.embedding_generator = EmbeddingGenerator(
            model_name=self.config.EMBEDDING_MODEL
        )

        # 初始化FAISS索引
        self.faiss_index = FAISSIndex(self.embedding_generator.embedding_dim)

        self.is_initialized = True
        logger.info("系统初始化完成")

    def build_index_from_directory(self, data_dir: Optional[str] = None) -> None:
        """从目录构建索引"""
        if not self.is_initialized:
            raise ValueError("系统尚未初始化")

        # 使用配置的目录或指定的目录
        target_data_dir = data_dir if data_dir else self.config.DATA_DIR

        logger.info(f"从目录构建索引: {target_data_dir}")

        # 1. 加载文档
        documents = self.document_loader.load_all_documents(target_data_dir)
        if not documents:
            logger.error("没有找到可用的文档")
            return

        # 2. 分割文本
        chunks = self.text_processor.split_documents(documents)

        # 3. 生成嵌入向量
        texts = [chunk['content'] for chunk in chunks]
        logger.info(f"生成嵌入向量，共 {len(texts)} 个文本块...")
        embeddings = self.embedding_generator.generate_embeddings(texts)

        # 4. 构建索引
        self.faiss_index.build_index(embeddings, chunks)

        # 5. 保存索引和元数据到数据库
        index_path = self.config.get_index_path()
        meta_path = self.config.get_meta_path()
        self.faiss_index.save_index(index_path, meta_path)
        
        # 将元数据保存到数据库
        self.db_manager.save_chunks(chunks)
        # 更新已处理文件列表
        self.db_manager.update_processed_files([doc['full_path'] for doc in documents])

        logger.info("索引构建并已存入数据库")

    def update_index_from_directory(self, data_dir: Optional[str] = None) -> None:
        """从目录增量更新索引"""
        if not self.is_initialized:
            raise ValueError("系统尚未初始化")

        target_data_dir = data_dir if data_dir else self.config.DATA_DIR
        logger.info(f"从目录增量更新索引: {target_data_dir}")

        # 1. 加载现有索引和已处理文件列表
        self.load_existing_index()
        processed_files = self.db_manager.get_processed_files()

        # 2. 加载新/已修改的文档
        documents = self.document_loader.load_all_documents(target_data_dir, processed_files)
        if not documents:
            logger.info("没有找到需要更新的文档")
            return

        # 移除已更新文件的旧数据
        for doc in documents:
            self.db_manager.remove_chunks_by_file_path(doc['file_path'])

        # 3. 分割、生成嵌入并添加到索引
        chunks = self.text_processor.split_documents(documents)
        texts = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_generator.generate_embeddings(texts)
        self.faiss_index.add(embeddings, chunks)

        # 4. 保存更新后的索引和数据库
        self.faiss_index.save_index(self.config.get_index_path(), self.config.get_meta_path())
        self.db_manager.save_chunks(chunks, overwrite=False) # 追加新的chunks
        self.db_manager.update_processed_files([doc['full_path'] for doc in documents])

        logger.info("索引增量更新完成")

    def load_existing_index(self) -> None:
        """加载现有索引"""
        if not self.is_initialized:
            raise ValueError("系统尚未初始化")

        index_path = self.config.get_index_path()
        meta_path = self.config.get_meta_path()
        db_path = self.config.get_db_path()

        # 检查索引文件是否存在
        if not os.path.exists(index_path):
            logger.warning("索引文件不存在，请先构建索引")
            return

        # 优先从数据库加载元数据
        if os.path.exists(db_path):
            try:
                logger.info(f"从数据库加载元数据: {db_path}")
                self.faiss_index.index = faiss.read_index(index_path)
                self.faiss_index.metadata = self.db_manager.load_all_chunks()
                logger.info(f"索引已加载，包含 {self.faiss_index.index.ntotal} 个向量")
                return
            except Exception as e:
                logger.error(f"从数据库加载元数据失败: {e}，尝试从pickle加载")

        # 降级从 pickle 加载
        if not os.path.exists(meta_path):
            logger.warning("元数据文件(pickle)不存在，无法完成加载")
            return

        self.faiss_index.load_index(index_path, meta_path)
        logger.info("现有索引加载完成")

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索操作手册"""
        if not self.is_initialized:
            raise ValueError("系统尚未初始化")
        if self.faiss_index.index is None:
            raise ValueError("索引尚未加载或构建")

        k = top_k if top_k is not None else self.config.TOP_K

        # 生成查询嵌入
        query_embedding = self.embedding_generator.generate_embeddings([query])[0]

        # 搜索
        results = self.faiss_index.search(query_embedding, k)

        return results

    def interactive_search(self) -> None:
        """交互式搜索模式"""
        if not self.is_initialized:
            self.initialize()

        if self.faiss_index.index is None:
            logger.info("索引未加载，尝试加载现有索引...")
            self.load_existing_index()

            if self.faiss_index.index is None:
                logger.info("没有找到现有索引，需要先构建索引")
                response = input("是否现在构建索引？(y/n): ")
                if response.lower() == 'y':
                    self.build_index_from_directory()
                else:
                    logger.info("退出交互模式")
                    return

        logger.info("进入交互式搜索模式，输入'quit'或'exit'退出")

        while True:
            try:
                query = input("\n请输入搜索查询: ").strip()

                if query.lower() in ['quit', 'exit', '退出']:
                    logger.info("退出交互模式")
                    break

                if not query:
                    print("查询不能为空")
                    continue

                # 执行搜索
                results = self.search(query)

                # 显示结果
                if not results:
                    print("没有找到相关结果")
                else:
                    print(f"\n找到 {len(results)} 个相关结果:")
                    print("=" * 80)

                    for i, result in enumerate(results):
                        print(f"\n{i+1}. [相似度: {result['similarity_score']:.3f}]")
                        print(f"   文件: {result['file_path']}")
                        print(f"   内容: {result['content'][:400]}...")
                        print("-" * 80)

            except KeyboardInterrupt:
                logger.info("\n用户中断搜索")
                break
            except Exception as e:
                logger.error(f"搜索出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='FAISS操作手册搜索系统')
    parser.add_argument('--mode', choices=['build', 'update', 'search', 'interactive'],
                       default='interactive', help='运行模式')
    parser.add_argument('--data-dir', type=str,
                       default=Config.DATA_DIR, help='数据目录路径')
    parser.add_argument('--query', type=str, help='搜索查询（search模式使用）')
    parser.add_argument('--top-k', type=int, default=Config.TOP_K,
                       help='返回结果数量')
    # The --use-openai and --use-deepseek arguments were removed as they are no longer supported.
    parser.add_argument('--config', type=str, help='配置文件路径')

    args = parser.parse_args()

    # 加载配置（如果有）
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(Config, key):
                        setattr(Config, key, value)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")

    # 更新配置
    if args.data_dir != Config.DATA_DIR:
        Config.DATA_DIR = args.data_dir
    if args.top_k != Config.TOP_K:
        Config.TOP_K = args.top_k

    # 创建系统实例
    system = ManualSearchSystem(Config)

    try:
        # 初始化系统
        system.initialize()

        if args.mode == 'build':
            # 构建索引模式
            logger.info("开始构建索引...")
            system.build_index_from_directory(args.data_dir)

        elif args.mode == 'update':
            # 更新索引模式
            logger.info("开始增量更新索引...")
            system.update_index_from_directory(args.data_dir)

        elif args.mode == 'search':
            # 搜索模式
            if not args.query:
                logger.error("搜索模式需要提供--query参数")
                parser.print_help()
                return

            # 尝试加载现有索引
            system.load_existing_index()

            if system.faiss_index.index is None:
                logger.error("索引不存在，请先运行构建模式")
                return

            # 执行搜索
            results = system.search(args.query, args.top_k)

            # 输出结果
            if not results:
                print("没有找到相关结果")
            else:
                print(f"查询: {args.query}")
                print(f"找到 {len(results)} 个相关结果:")
                print("=" * 80)

                for i, result in enumerate(results):
                    print(f"\n{i+1}. [相似度: {result['similarity_score']:.3f}]")
                    print(f"   文件: {result['file_path']}")
                    print(f"   内容: {result['content'][:500]}...")
                    print("-" * 80)

        else:
            # 交互模式
            system.interactive_search()

    except Exception as e:
        logger.error(f"系统运行出错: {e}")
        sys.exit(1)


def create_example_data():
    """创建示例数据和配置文件"""
    config = Config
    config.ensure_dirs()

    # 创建示例操作手册文件
    example_content = """操作手册示例

第一章：系统概述
本系统是一个基于FAISS向量数据库的操作手册搜索系统。
支持多种文档格式，包括TXT、PDF、DOCX等。

第二章：安装指南
1. 安装Python 3.8或更高版本
2. 安装依赖库：pip install -r requirements.txt
3. 准备操作手册文件，放入data目录
4. 运行python main.py --mode build构建索引
5. 运行python main.py --mode interactive进行交互搜索

第三章：使用说明
系统支持以下功能：
- 文档加载和分块处理
- 向量索引构建
- 相似度搜索
- 结果排名和显示

第四章：故障排除
常见问题：
1. 如果遇到依赖问题，请检查Python版本
2. 确保操作手册文件格式正确
3. 检查磁盘空间是否充足
"""

    # 写入示例文件
    example_file = os.path.join(config.DATA_DIR, "操作手册示例.txt")
    with open(example_file, 'w', encoding='utf-8') as f:
        f.write(example_content)

    print(f"已创建示例文件: {example_file}")

    # 创建配置文件示例
    config_example = {
        "DATA_DIR": "data",
        "INDEX_DIR": "index",
        "CHUNK_SIZE": 500,
        "CHUNK_OVERLAP": 50,
        "EMBEDDING_MODEL": "D:\\向量数据库\\all-MiniLM-L6-v2",
        "TOP_K": 5
    }

    config_file = "config.example.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_example, f, ensure_ascii=False, indent=2)

    print(f"已创建配置文件示例: {config_file}")

    # 创建requirements.txt
    requirements = """numpy>=1.21.0
faiss-cpu>=1.7.0
sentence-transformers>=2.2.0
langchain>=0.0.200
pypdf2>=3.0.0
python-docx>=0.8.11
openai>=0.27.0  # 可选，如果需要使用OpenAI嵌入
"""

    with open("requirements.txt", 'w', encoding='utf-8') as f:
        f.write(requirements)

    print("已创建requirements.txt")
    print("\n下一步：")
    print("1. 将您的操作手册文件放入data目录")
    print("2. 运行: python main.py --mode build 构建索引")
    print("3. 运行: python main.py --mode interactive 进行交互搜索")


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--create-example":
        create_example_data()
    else:
        main()