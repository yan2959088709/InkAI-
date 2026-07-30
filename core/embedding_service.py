"""
嵌入模型服务
负责生成文本的向量嵌入，用于语义搜索和RAG
"""

import requests
import json
import config
from typing import List, Dict, Any, Optional
import time
from utils.logger import get_logger
logger = get_logger("embedding_service")


class EmbeddingService:
    """嵌入模型服务"""
    
    def __init__(self):
        self.api_key = config.EMBEDDING_API_KEY
        self.base_url = config.EMBEDDING_BASE_URL
        self.model = config.EMBEDDING_MODEL
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        生成文本的向量嵌入

        Args:
            text: 要嵌入的文本

        Returns:
            向量嵌入列表，如果失败返回None
        """
        if not text or not text.strip():
            return None

        # [DEBUG] 记录文本长度和前100字符
        logger.info(f"[DEBUG] 嵌入文本长度: {len(text)} 字符, 前100字符: {text[:100]}")

        # [BUG FIX] 检查文本长度，避免API返回400错误
        MIN_TEXT_LENGTH = 10  # 阿里云Embedding可能有最小文本长度要求
        if len(text) < MIN_TEXT_LENGTH:
            logger.warning(f"⚠️ 文本过短 ({len(text)} < {MIN_TEXT_LENGTH})，跳过嵌入")
            return None

        try:
            # 构建API请求
            url = f"{self.base_url}/embeddings"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "input": text
            }
            
            # 重试机制
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # 提取嵌入向量
                    if "data" in result and len(result["data"]) > 0:
                        embedding = result["data"][0].get("embedding", [])
                        if embedding:
                            return embedding
                    
                    logger.error(f"⚠️ 嵌入API返回格式异常: {result}")
                    return None
                    
                except requests.exceptions.RequestException as e:
                    error_detail = f"{e}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_detail = f"{e} | Response: {e.response.text[:500] if e.response.text else 'empty'}"
                    if attempt < self.max_retries - 1:
                        logger.error(f"⚠️ 嵌入API调用失败（尝试 {attempt + 1}/{self.max_retries}）: {error_detail}，重试中...")
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"❌ 嵌入API调用失败（已重试{self.max_retries}次）: {error_detail}")
                        return None
            
            return None
            
        except Exception as e:
            logger.info(f"❌ 生成嵌入向量时出错: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量生成文本的向量嵌入
        
        Args:
            texts: 要嵌入的文本列表
            
        Returns:
            向量嵌入列表（与输入文本顺序对应）
        """
        if not texts:
            return []
        
        try:
            # 构建API请求
            url = f"{self.base_url}/embeddings"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "input": texts
            }
            
            # 重试机制
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=60)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # 提取嵌入向量
                    if "data" in result and len(result["data"]) > 0:
                        embeddings = []
                        for item in result["data"]:
                            embedding = item.get("embedding", [])
                            embeddings.append(embedding if embedding else None)
                        return embeddings
                    
                    logger.error(f"⚠️ 批量嵌入API返回格式异常: {result}")
                    # 如果批量失败，回退到单个生成
                    return [self.generate_embedding(text) for text in texts]
                    
                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries - 1:
                        logger.error(f"⚠️ 批量嵌入API调用失败（尝试 {attempt + 1}/{self.max_retries}）: {e}，重试中...")
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"❌ 批量嵌入API调用失败（已重试{self.max_retries}次）: {e}")
                        # 回退到单个生成
                        return [self.generate_embedding(text) for text in texts]
            
            # 如果所有重试都失败，回退到单个生成
            return [self.generate_embedding(text) for text in texts]
            
        except Exception as e:
            logger.info(f"❌ 批量生成嵌入向量时出错: {e}")
            # 回退到单个生成
            return [self.generate_embedding(text) for text in texts]
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个嵌入向量的余弦相似度
        
        Args:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量
            
        Returns:
            相似度分数（0-1之间）
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            return 0.0
        
        try:
            # 计算余弦相似度
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            return max(0.0, min(1.0, similarity))  # 确保在0-1之间
            
        except Exception as e:
            logger.info(f"❌ 计算相似度时出错: {e}")
            return 0.0

