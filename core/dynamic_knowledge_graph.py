"""
[DEPRECATED] 动态知识图谱系统（旧流水线遗留）

⚠ 注意命名陷阱：本模块（DynamicKnowledgeGraph）与新流水线在用的
   core/dynamic_knowledge_manager.py（DynamicKnowledgeManager）是**两个不同的东西**：
   - 本模块：旧 workflow 的图状知识管理，落盘 dynamic_knowledge.json，已废弃
   - 新模块：DKM，落盘 dynamic_state/state.json，仍在使用

新代码请勿 import 本模块。

详见：docs/development/data_files_catalog.md
"""
import warnings as _warnings
_warnings.warn(
    "core.dynamic_knowledge_graph 已废弃；新流水线请使用 core.dynamic_knowledge_manager。"
    "详见 docs/development/data_files_catalog.md",
    DeprecationWarning,
    stacklevel=2,
)

import json
import os
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import networkx as nx
from collections import defaultdict
from utils.logger import get_logger
logger = get_logger("dynamic_knowledge_graph")


class KnowledgeNode:
    """知识图谱节点"""
    
    def __init__(self, node_id: str, node_type: str, properties: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = node_type  # character, event, location, concept, object
        self.properties = properties or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.version = 1
    
    def update_properties(self, new_properties: Dict[str, Any]) -> bool:
        """更新节点属性"""
        try:
            # 合并属性
            for key, value in new_properties.items():
                if key in self.properties:
                    # 如果属性已存在，创建版本历史
                    if not hasattr(self, 'property_history'):
                        self.property_history = {}
                    if key not in self.property_history:
                        self.property_history[key] = []
                    self.property_history[key].append({
                        "old_value": self.properties[key],
                        "new_value": value,
                        "timestamp": datetime.now().isoformat()
                    })
                
                self.properties[key] = value
            
            self.updated_at = datetime.now().isoformat()
            self.version += 1
            return True
        except Exception as e:
            logger.error(f"更新节点属性失败: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "property_history": getattr(self, 'property_history', {})
        }


class KnowledgeEdge:
    """知识图谱边"""
    
    def __init__(self, source_id: str, target_id: str, relationship_type: str, properties: Dict[str, Any] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type
        self.properties = properties or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.strength = 1.0  # 关系强度
    
    def update_strength(self, new_strength: float) -> bool:
        """更新关系强度"""
        try:
            self.strength = max(0.0, min(1.0, new_strength))
            self.updated_at = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"更新关系强度失败: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "properties": self.properties,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "strength": self.strength
        }


class DynamicKnowledgeGraph:
    """动态知识图谱"""
    
    def __init__(self, novel_id: str, data_manager=None):
        self.novel_id = novel_id
        self.data_manager = data_manager
        self.file_path = f"data/novels/{novel_id}/knowledge_graph.json"
        
        # 图谱数据结构
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: Dict[Tuple[str, str], KnowledgeEdge] = {}
        self.graph = nx.DiGraph()  # 使用NetworkX作为底层图结构
        
        # 版本管理
        self.version_history = []
        self.current_version = 1
        
        # 缓存
        self.cache = {
            "entity_cache": {},
            "relationship_cache": {},
            "query_cache": {}
        }
        
        # 加载现有图谱
        self.load_graph()
    
    def load_graph(self) -> bool:
        """加载知识图谱"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                
                # 加载节点
                for node_data in graph_data.get("nodes", []):
                    node = KnowledgeNode(
                        node_data["node_id"],
                        node_data["node_type"],
                        node_data["properties"]
                    )
                    node.created_at = node_data.get("created_at", node.created_at)
                    node.updated_at = node_data.get("updated_at", node.updated_at)
                    node.version = node_data.get("version", 1)
                    node.property_history = node_data.get("property_history", {})
                    
                    self.nodes[node.node_id] = node
                    self.graph.add_node(node.node_id, **node.to_dict())
                
                # 加载边
                for edge_data in graph_data.get("edges", []):
                    edge = KnowledgeEdge(
                        edge_data["source_id"],
                        edge_data["target_id"],
                        edge_data["relationship_type"],
                        edge_data["properties"]
                    )
                    edge.created_at = edge_data.get("created_at", edge.created_at)
                    edge.updated_at = edge_data.get("updated_at", edge.updated_at)
                    edge.strength = edge_data.get("strength", 1.0)
                    
                    edge_key = (edge.source_id, edge.target_id)
                    self.edges[edge_key] = edge
                    self.graph.add_edge(
                        edge.source_id, 
                        edge.target_id, 
                        **edge.to_dict()
                    )
                
                self.current_version = graph_data.get("current_version", 1)
                self.version_history = graph_data.get("version_history", [])
                
                return True
            else:
                # 创建初始图谱
                self._create_initial_graph()
                return True
                
        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")
            return False
    
    def save_graph(self) -> bool:
        """保存知识图谱"""
        try:
            graph_data = {
                "novel_id": self.novel_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "current_version": self.current_version,
                "version_history": self.version_history,
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "edges": [edge.to_dict() for edge in self.edges.values()],
                "statistics": self.get_statistics()
            }
            
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
            return False
    
    def _create_initial_graph(self):
        """创建初始知识图谱"""
        # 创建基础节点类型
        self._create_base_node_types()
        
        # 保存初始图谱
        self.save_graph()
    
    def _create_base_node_types(self):
        """创建基础节点类型"""
        base_types = [
            ("main_character", "character"),
            ("supporting_character", "character"),
            ("antagonist", "character"),
            ("world", "location"),
            ("main_setting", "location"),
            ("core_concept", "concept"),
            ("main_theme", "concept")
        ]
        
        for node_id, node_type in base_types:
            self.add_node(node_id, node_type, {"description": f"基础{node_type}节点"})
    
    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any] = None) -> bool:
        """添加节点"""
        try:
            if node_id in self.nodes:
                # 更新现有节点
                return self.update_node(node_id, properties or {})
            
            node = KnowledgeNode(node_id, node_type, properties)
            self.nodes[node_id] = node
            self.graph.add_node(node_id, **node.to_dict())
            
            # 清理相关缓存
            self._clear_cache_for_node(node_id)
            
            return True
        except Exception as e:
            logger.error(f"添加节点失败: {e}")
            return False
    
    def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """更新节点"""
        try:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            success = node.update_properties(properties)
            
            if success:
                # 更新图中的节点数据
                self.graph.nodes[node_id].update(node.to_dict())
                
                # 清理相关缓存
                self._clear_cache_for_node(node_id)
            
            return success
        except Exception as e:
            logger.error(f"更新节点失败: {e}")
            return False
    
    def add_edge(self, source_id: str, target_id: str, relationship_type: str, properties: Dict[str, Any] = None) -> bool:
        """添加边"""
        try:
            edge_key = (source_id, target_id)
            
            if edge_key in self.edges:
                # 更新现有边
                edge = self.edges[edge_key]
                edge.properties.update(properties or {})
                edge.updated_at = datetime.now().isoformat()
            else:
                # 创建新边
                edge = KnowledgeEdge(source_id, target_id, relationship_type, properties)
                self.edges[edge_key] = edge
            
            # 更新图中的边
            self.graph.add_edge(source_id, target_id, **edge.to_dict())
            
            # 清理相关缓存
            self._clear_cache_for_edge(source_id, target_id)
            
            return True
        except Exception as e:
            logger.error(f"添加边失败: {e}")
            return False
    
    def update_from_chapter(self, chapter: int, content: Dict[str, Any]) -> bool:
        """从章节内容更新知识图谱"""
        try:
            # 提取知识
            extracted_knowledge = self._extract_knowledge_from_content(content)
            
            # 更新图谱
            self._update_graph_with_knowledge(chapter, extracted_knowledge)
            
            # 验证一致性
            inconsistencies = self._validate_consistency()
            if inconsistencies:
                self._resolve_conflicts(inconsistencies)
            
            # 保存版本
            self._save_version(chapter)
            
            # 保存图谱
            self.save_graph()
            
            return True
        except Exception as e:
            logger.error(f"从章节更新知识图谱失败: {e}")
            return False
    
    def _extract_knowledge_from_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """从内容中提取知识"""
        extracted = {
            "entities": [],
            "relationships": [],
            "events": [],
            "properties": {},
            "timeline": []
        }
        
        text_content = content.get("content", "")
        
        # 简单的实体提取（实际应该用NLP技术）
        entities = self._extract_entities_simple(text_content)
        extracted["entities"] = entities
        
        # 关系提取
        relationships = self._extract_relationships_simple(text_content)
        extracted["relationships"] = relationships
        
        # 事件提取
        events = self._extract_events_simple(text_content)
        extracted["events"] = events
        
        # 属性变化提取
        properties = self._extract_property_changes(text_content)
        extracted["properties"] = properties
        
        return extracted
    
    def _extract_entities_simple(self, text: str) -> List[Dict[str, Any]]:
        """简单的实体提取"""
        entities = []
        
        # 关键词匹配（实际应该用更复杂的NLP）
        entity_patterns = {
            "character": ["主角", "英雄", "反派", "敌人", "朋友", "老师", "学生"],
            "location": ["城市", "村庄", "森林", "山脉", "河流", "宫殿", "城堡"],
            "object": ["剑", "魔法", "宝物", "书籍", "武器", "装备"],
            "concept": ["力量", "智慧", "勇气", "爱情", "仇恨", "命运"]
        }
        
        for entity_type, patterns in entity_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    entities.append({
                        "name": pattern,
                        "type": entity_type,
                        "context": self._get_context_around(text, pattern)
                    })
        
        return entities
    
    def _extract_relationships_simple(self, text: str) -> List[Dict[str, Any]]:
        """简单的关系提取"""
        relationships = []
        
        # 关系模式
        relationship_patterns = [
            ("是", "identity"),
            ("有", "possession"),
            ("喜欢", "like"),
            ("讨厌", "dislike"),
            ("攻击", "attack"),
            ("帮助", "help"),
            ("跟随", "follow")
        ]
        
        for pattern, relation_type in relationship_patterns:
            if pattern in text:
                relationships.append({
                    "relation_type": relation_type,
                    "pattern": pattern,
                    "context": self._get_context_around(text, pattern)
                })
        
        return relationships
    
    def _extract_events_simple(self, text: str) -> List[Dict[str, Any]]:
        """简单的事件提取"""
        events = []
        
        # 事件关键词
        event_keywords = ["发生", "出现", "发现", "遇到", "战斗", "对话", "学习", "成长"]
        
        for keyword in event_keywords:
            if keyword in text:
                events.append({
                    "event_type": keyword,
                    "context": self._get_context_around(text, keyword)
                })
        
        return events
    
    def _extract_property_changes(self, text: str) -> Dict[str, Any]:
        """提取属性变化"""
        changes = {}
        
        # 属性变化模式
        change_patterns = {
            "能力": ["学会", "掌握", "提升", "增强"],
            "情感": ["高兴", "愤怒", "悲伤", "恐惧"],
            "状态": ["健康", "受伤", "疲惫", "兴奋"]
        }
        
        for property_name, patterns in change_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    if property_name not in changes:
                        changes[property_name] = []
                    changes[property_name].append({
                        "change_type": pattern,
                        "context": self._get_context_around(text, pattern)
                    })
        
        return changes
    
    def _get_context_around(self, text: str, pattern: str, context_length: int = 50) -> str:
        """获取关键词周围的上下文"""
        try:
            index = text.find(pattern)
            if index == -1:
                return ""
            
            start = max(0, index - context_length)
            end = min(len(text), index + len(pattern) + context_length)
            
            return text[start:end]
        except Exception as e:
            return ""
    
    def _update_graph_with_knowledge(self, chapter: int, knowledge: Dict[str, Any]):
        """用提取的知识更新图谱"""
        
        # 更新实体节点
        for entity in knowledge.get("entities", []):
            node_id = f"{entity['type']}_{entity['name']}"
            self.add_node(node_id, entity["type"], {
                "name": entity["name"],
                "first_appearance": chapter,
                "context": entity.get("context", ""),
                "last_mentioned": chapter
            })
        
        # 更新关系边
        for relationship in knowledge.get("relationships", []):
            # 这里需要更复杂的逻辑来匹配源节点和目标节点
            # 简化实现
            pass
        
        # 更新事件节点
        for event in knowledge.get("events", []):
            event_id = f"event_{chapter}_{hashlib.md5(event['context'].encode()).hexdigest()[:8]}"
            self.add_node(event_id, "event", {
                "event_type": event["event_type"],
                "chapter": chapter,
                "context": event.get("context", "")
            })
        
        # 更新属性变化
        for entity_id, entity in self.nodes.items():
            if entity.node_type == "character":
                property_changes = knowledge.get("properties", {})
                for prop_name, changes in property_changes.items():
                    for change in changes:
                        # 更新角色属性
                        current_props = entity.properties.get(prop_name, {})
                        current_props[f"chapter_{chapter}"] = change["change_type"]
                        entity.update_properties({prop_name: current_props})
    
    def _validate_consistency(self) -> List[Dict[str, Any]]:
        """验证图谱一致性"""
        inconsistencies = []
        
        # 检查孤立节点
        isolated_nodes = list(nx.isolates(self.graph))
        if isolated_nodes:
            inconsistencies.append({
                "type": "isolated_nodes",
                "nodes": isolated_nodes,
                "description": "发现孤立节点"
            })
        
        # 检查循环依赖
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                inconsistencies.append({
                    "type": "cycles",
                    "cycles": cycles,
                    "description": "发现循环依赖"
                })
        except Exception as e:
            pass
        
        # 检查属性一致性
        for node_id, node in self.nodes.items():
            if node.node_type == "character":
                # 检查角色属性的一致性
                if "age" in node.properties and "birth_year" in node.properties:
                    # 简单的年龄一致性检查
                    pass
        
        return inconsistencies
    
    def _resolve_conflicts(self, inconsistencies: List[Dict[str, Any]]):
        """解决冲突"""
        for inconsistency in inconsistencies:
            if inconsistency["type"] == "isolated_nodes":
                # 尝试为孤立节点创建关系
                self._connect_isolated_nodes(inconsistency["nodes"])
            elif inconsistency["type"] == "cycles":
                # 打破循环依赖
                self._break_cycles(inconsistency["cycles"])
    
    def _connect_isolated_nodes(self, isolated_nodes: List[str]):
        """连接孤立节点"""
        # 简单的连接策略：连接到最近的相关节点
        for node_id in isolated_nodes:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                # 寻找相关节点
                for other_node_id, other_node in self.nodes.items():
                    if (other_node_id != node_id and 
                        other_node.node_type == node.node_type and
                        not self.graph.has_edge(node_id, other_node_id)):
                        
                        # 添加关系
                        self.add_edge(node_id, other_node_id, "related", {
                            "connection_type": "similarity"
                        })
                        break
    
    def _break_cycles(self, cycles: List[List[str]]):
        """打破循环"""
        for cycle in cycles:
            if len(cycle) > 1:
                # 删除循环中的一条边
                source, target = cycle[0], cycle[1]
                if (source, target) in self.edges:
                    del self.edges[(source, target)]
                    if self.graph.has_edge(source, target):
                        self.graph.remove_edge(source, target)
    
    def _save_version(self, chapter: int):
        """保存版本"""
        version_data = {
            "version": self.current_version,
            "chapter": chapter,
            "timestamp": datetime.now().isoformat(),
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "statistics": self.get_statistics()
        }
        
        self.version_history.append(version_data)
        self.current_version += 1
    
    def _clear_cache_for_node(self, node_id: str):
        """清理节点相关缓存"""
        # 清理实体缓存
        if node_id in self.cache["entity_cache"]:
            del self.cache["entity_cache"][node_id]
        
        # 清理查询缓存
        self.cache["query_cache"].clear()
    
    def _clear_cache_for_edge(self, source_id: str, target_id: str):
        """清理边相关缓存"""
        edge_key = f"{source_id}_{target_id}"
        if edge_key in self.cache["relationship_cache"]:
            del self.cache["relationship_cache"][edge_key]
        
        # 清理查询缓存
        self.cache["query_cache"].clear()
    
    def get_context_for_generation(self, chapter: int) -> Dict[str, Any]:
        """获取生成所需的上下文"""
        try:
            # 获取相关实体
            relevant_entities = self._get_relevant_entities(chapter)
            
            # 获取关系网络
            relationship_network = self._get_relationship_network(relevant_entities)
            
            # 获取事件时间线
            event_timeline = self._get_event_timeline(chapter)
            
            # 获取属性变化
            property_changes = self._get_property_changes_history(chapter)
            
            return {
                "entities": relevant_entities,
                "relationships": relationship_network,
                "timeline": event_timeline,
                "properties": property_changes,
                "graph_version": self.current_version,
                "node_count": len(self.nodes),
                "edge_count": len(self.edges)
            }
            
        except Exception as e:
            logger.error(f"获取生成上下文失败: {e}")
            return {}
    
    def _get_relevant_entities(self, chapter: int) -> List[Dict[str, Any]]:
        """获取相关实体"""
        relevant_entities = []
        
        for node_id, node in self.nodes.items():
            if node.node_type in ["character", "location", "concept"]:
                # 检查实体是否在最近章节中出现
                last_mentioned = node.properties.get("last_mentioned", 0)
                if last_mentioned >= chapter - 5:  # 最近5章内出现
                    relevant_entities.append({
                        "node_id": node_id,
                        "type": node.node_type,
                        "properties": node.properties,
                        "relevance_score": self._calculate_relevance_score(node, chapter)
                    })
        
        # 按相关性排序
        relevant_entities.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return relevant_entities[:20]  # 返回最相关的20个实体
    
    def _calculate_relevance_score(self, node: KnowledgeNode, chapter: int) -> float:
        """计算实体相关性分数"""
        score = 0.0
        
        # 最近出现加分
        last_mentioned = node.properties.get("last_mentioned", 0)
        if last_mentioned >= chapter - 2:
            score += 1.0
        elif last_mentioned >= chapter - 5:
            score += 0.5
        
        # 出现频率加分
        appearance_count = node.properties.get("appearance_count", 1)
        score += min(appearance_count / 10, 1.0)
        
        # 重要性加分
        importance = node.properties.get("importance", 0.5)
        score += importance
        
        return score
    
    def _get_relationship_network(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """获取关系网络"""
        relationship_network = []
        entity_ids = [entity["node_id"] for entity in entities]
        
        for source_id in entity_ids:
            for target_id in entity_ids:
                if source_id != target_id:
                    edge_key = (source_id, target_id)
                    if edge_key in self.edges:
                        edge = self.edges[edge_key]
                        relationship_network.append({
                            "source": source_id,
                            "target": target_id,
                            "relationship_type": edge.relationship_type,
                            "strength": edge.strength,
                            "properties": edge.properties
                        })
        
        return relationship_network
    
    def _get_event_timeline(self, chapter: int) -> List[Dict[str, Any]]:
        """获取事件时间线"""
        timeline = []
        
        for node_id, node in self.nodes.items():
            if node.node_type == "event":
                event_chapter = node.properties.get("chapter", 0)
                if event_chapter <= chapter and event_chapter >= chapter - 10:
                    timeline.append({
                        "event_id": node_id,
                        "chapter": event_chapter,
                        "event_type": node.properties.get("event_type", ""),
                        "context": node.properties.get("context", "")
                    })
        
        # 按章节排序
        timeline.sort(key=lambda x: x["chapter"])
        
        return timeline
    
    def _get_property_changes_history(self, chapter: int) -> Dict[str, Any]:
        """获取属性变化历史"""
        property_changes = {}
        
        for node_id, node in self.nodes.items():
            if node.node_type == "character":
                character_changes = {}
                for prop_name, prop_value in node.properties.items():
                    if isinstance(prop_value, dict):
                        # 属性变化历史
                        recent_changes = []
                        for chapter_key, change_value in prop_value.items():
                            if chapter_key.startswith("chapter_") and int(chapter_key.split("_")[1]) >= chapter - 5:
                                recent_changes.append({
                                    "chapter": int(chapter_key.split("_")[1]),
                                    "change": change_value
                                })
                        
                        if recent_changes:
                            character_changes[prop_name] = recent_changes
                
                if character_changes:
                    property_changes[node_id] = character_changes
        
        return property_changes
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        node_types = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.node_type] += 1
        
        relationship_types = defaultdict(int)
        for edge in self.edges.values():
            relationship_types[edge.relationship_type] += 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "relationship_types": dict(relationship_types),
            "graph_density": nx.density(self.graph),
            "connected_components": nx.number_weakly_connected_components(self.graph),
            "current_version": self.current_version
        }
    
    def query_graph(self, query: str) -> Dict[str, Any]:
        """查询图谱"""
        try:
            # 简单的查询实现
            if "角色" in query or "character" in query.lower():
                return self._query_characters()
            elif "关系" in query or "relationship" in query.lower():
                return self._query_relationships()
            elif "事件" in query or "event" in query.lower():
                return self._query_events()
            else:
                return {"error": "无法理解查询"}
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    def _query_characters(self) -> Dict[str, Any]:
        """查询角色"""
        characters = []
        for node_id, node in self.nodes.items():
            if node.node_type == "character":
                characters.append(node.to_dict())
        
        return {
            "query_type": "characters",
            "results": characters,
            "count": len(characters)
        }
    
    def _query_relationships(self) -> Dict[str, Any]:
        """查询关系"""
        relationships = []
        for edge in self.edges.values():
            relationships.append(edge.to_dict())
        
        return {
            "query_type": "relationships",
            "results": relationships,
            "count": len(relationships)
        }
    
    def _query_events(self) -> Dict[str, Any]:
        """查询事件"""
        events = []
        for node_id, node in self.nodes.items():
            if node.node_type == "event":
                events.append(node.to_dict())
        
        return {
            "query_type": "events",
            "results": events,
            "count": len(events)
        }
