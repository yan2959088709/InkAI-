"""
向量数据库
负责存储和检索向量嵌入，支持语义搜索
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import threading
from utils.logger import get_logger
logger = get_logger("vector_database")


class VectorDatabase:
    """向量数据库（基于文件的简单实现）"""
    
    def __init__(self, data_manager=None, embedding_service=None):
        self.data_manager = data_manager
        self.embedding_service = embedding_service
        self.vectors_dir = "data/vectors"
        self.lock = threading.Lock()
        
        # 确保目录存在
        os.makedirs(self.vectors_dir, exist_ok=True)
    
    def _get_vector_file_path(self, novel_id: str) -> str:
        """获取向量文件路径"""
        return os.path.join(self.vectors_dir, f"{novel_id}_vectors.json")
    
    def _load_vectors(self, novel_id: str) -> Dict[str, Any]:
        """加载向量数据"""
        file_path = self._get_vector_file_path(novel_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"⚠️ 加载向量数据失败: {e}")
                return {"vectors": {}, "metadata": {}}
        return {"vectors": {}, "metadata": {}}
    
    def _save_vectors(self, novel_id: str, data: Dict[str, Any]) -> bool:
        """保存向量数据"""
        try:
            file_path = self._get_vector_file_path(novel_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"❌ 保存向量数据失败: {e}")
            return False
    
    def add_vector(self, novel_id: str, doc_id: str, text: str, 
                   metadata: Dict[str, Any] = None, embedding: List[float] = None) -> bool:
        """
        添加向量到数据库
        
        Args:
            novel_id: 小说ID
            doc_id: 文档ID（如章节号、角色名等）
            text: 文档文本
            metadata: 元数据
            embedding: 预计算的嵌入向量（如果为None则自动生成）
            
        Returns:
            是否成功
        """
        try:
            with self.lock:
                # 加载现有数据
                data = self._load_vectors(novel_id)
                vectors = data.get("vectors", {})
                metadata_dict = data.get("metadata", {})
                
                # 生成嵌入向量
                if embedding is None:
                    if not self.embedding_service:
                        logger.info("⚠️ 嵌入服务未初始化，无法生成向量")
                        return False
                    embedding = self.embedding_service.generate_embedding(text)
                    if not embedding:
                        logger.info(f"⚠️ 无法为文档 {doc_id} 生成嵌入向量")
                        return False
                
                # 存储向量和元数据
                vectors[doc_id] = {
                    "embedding": embedding,
                    "text": text,
                    "updated_at": datetime.now().isoformat()
                }
                
                if metadata:
                    metadata_dict[doc_id] = metadata
                
                # 保存数据
                data["vectors"] = vectors
                data["metadata"] = metadata_dict
                data["updated_at"] = datetime.now().isoformat()
                
                return self._save_vectors(novel_id, data)
                
        except Exception as e:
            logger.error(f"❌ 添加向量失败: {e}")
            return False
    
    def search_similar(self, novel_id: str, query_text: str, top_k: int = 5,
                      threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        语义搜索相似文档
        
        Args:
            novel_id: 小说ID
            query_text: 查询文本
            top_k: 返回前k个结果
            threshold: 相似度阈值
            
        Returns:
            相似文档列表（按相似度排序）
        """
        try:
            if not self.embedding_service:
                logger.info("⚠️ 嵌入服务未初始化，无法进行语义搜索")
                return []
            
            # 生成查询向量
            query_embedding = self.embedding_service.generate_embedding(query_text)
            if not query_embedding:
                logger.info("⚠️ 无法为查询文本生成嵌入向量")
                return []
            
            # 加载向量数据
            data = self._load_vectors(novel_id)
            vectors = data.get("vectors", {})
            metadata_dict = data.get("metadata", {})
            
            if not vectors:
                return []
            
            # 计算相似度
            similarities = []
            for doc_id, doc_data in vectors.items():
                doc_embedding = doc_data.get("embedding", [])
                if not doc_embedding:
                    continue
                
                similarity = self.embedding_service.calculate_similarity(
                    query_embedding, doc_embedding
                )
                
                if similarity >= threshold:
                    result = {
                        "doc_id": doc_id,
                        "text": doc_data.get("text", ""),
                        "similarity": similarity,
                        "metadata": metadata_dict.get(doc_id, {})
                    }
                    similarities.append(result)
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 返回前k个结果
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"❌ 语义搜索失败: {e}")
            return []
    
    def delete_vector(self, novel_id: str, doc_id: str) -> bool:
        """删除向量"""
        try:
            with self.lock:
                data = self._load_vectors(novel_id)
                vectors = data.get("vectors", {})
                metadata_dict = data.get("metadata", {})
                
                if doc_id in vectors:
                    del vectors[doc_id]
                if doc_id in metadata_dict:
                    del metadata_dict[doc_id]
                
                data["vectors"] = vectors
                data["metadata"] = metadata_dict
                data["updated_at"] = datetime.now().isoformat()
                
                return self._save_vectors(novel_id, data)
                
        except Exception as e:
            logger.error(f"❌ 删除向量失败: {e}")
            return False
    
    def get_vector_count(self, novel_id: str) -> int:
        """获取向量数量"""
        try:
            data = self._load_vectors(novel_id)
            return len(data.get("vectors", {}))
        except Exception as e:
            logger.error(f"⚠️ 获取向量数量失败: {e}")
            return 0

