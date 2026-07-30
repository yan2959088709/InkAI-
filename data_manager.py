"""
数据管理器
负责管理小说数据集和知识图谱
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import config
from utils.json_fixer import JsonFixer
from utils.logger import get_logger

logger = get_logger("data_manager")


class DataManager:
    """数据管理器类"""
    
    def __init__(self):
        self.novels_dir = config.NOVELS_DIR
        self.knowledge_graphs_dir = config.KNOWLEDGE_GRAPHS_DIR
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目录存在"""
        os.makedirs(self.novels_dir, exist_ok=True)
        os.makedirs(self.knowledge_graphs_dir, exist_ok=True)
    
    def create_novel_project(self, novel_data: Dict[str, Any]) -> str:
        """创建新小说项目"""
        novel_id = str(uuid.uuid4())
        novel_dir = os.path.join(self.novels_dir, novel_id)
        os.makedirs(novel_dir, exist_ok=True)
        
        # 保存小说元数据
        metadata = {
            "novel_id": novel_id,
            "title": novel_data.get("title", "未命名小说"),
            "user_requirements": novel_data.get("user_requirements", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "in_progress",
            "tags": novel_data.get("tags", {}),
            "characters": novel_data.get("characters", {}),
            "storyline": novel_data.get("storyline", {}),
            "chapters": []
        }
        
        metadata_file = os.path.join(novel_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return novel_id
    
    def save_novel_data(self, novel_id: str, data_type: str, data: Dict[str, Any]) -> bool:
        """保存小说数据"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                return False
            
            # 标准化数据格式，确保没有嵌套的JSON字符串
            standardized_data = self._standardize_data_format(data, data_type)
            
            # 保存数据到对应文件
            data_file = os.path.join(novel_dir, f"{data_type}.json")
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(standardized_data, f, ensure_ascii=False, indent=2)
            
            # 更新元数据
            self._update_metadata(novel_id, data_type, standardized_data)
            
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False
    
    def load_novel_data(self, novel_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """加载小说数据"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            data_file = os.path.join(novel_dir, f"{data_type}.json")
            
            if not os.path.exists(data_file):
                return None
            
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return None
    
    def save_chapter(self, novel_id: str, chapter_number: int, chapter_content: Dict[str, Any]) -> bool:
        """保存章节内容"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                logger.info(f"小说目录不存在: {novel_dir}")
                return False
            
            # 确保章节数据包含 word_count 字段（兜底保障）
            if 'word_count' not in chapter_content or chapter_content['word_count'] == 0:
                content = chapter_content.get('content', '')
                if content:
                    # 计算实际字数（去除空白字符）
                    clean_content = content.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\u3000', '')
                    chapter_content['word_count'] = len(clean_content)
                    logger.info(f"自动计算章节字数: {chapter_content['word_count']}")
                else:
                    chapter_content['word_count'] = 0
            
            # 确保包含创建时间
            if 'created_at' not in chapter_content:
                chapter_content['created_at'] = datetime.now().isoformat()
            
            # 保存章节JSON文件
            chapter_file = os.path.join(novel_dir, f"chapter_{chapter_number:03d}.json")
            with open(chapter_file, 'w', encoding='utf-8') as f:
                json.dump(chapter_content, f, ensure_ascii=False, indent=2)
            logger.info(f"章节JSON文件保存成功: {chapter_file}")
            
            # 保存章节TXT文件
            txt_file = self.save_chapter_txt(novel_id, chapter_number, chapter_content)
            if not txt_file:
                logger.error(f"章节TXT文件保存失败")
                return False
            logger.info(f"章节TXT文件保存成功: {txt_file}")
            
            # 更新元数据中的章节列表
            metadata_success = self._update_chapter_list(novel_id, chapter_number, chapter_content)
            if not metadata_success:
                logger.error(f"元数据更新失败")
                return False
            
            logger.info(f"章节{chapter_number}保存完全成功")
            return True
            
        except Exception as e:
            logger.error(f"保存章节失败: {e}")
            return False
    
    def get_chapters(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取小说的所有章节"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                return []
            
            chapters = []
            # 查找所有章节JSON文件
            for filename in os.listdir(novel_dir):
                if filename.startswith("chapter_") and filename.endswith(".json"):
                    chapter_file = os.path.join(novel_dir, filename)
                    try:
                        with open(chapter_file, 'r', encoding='utf-8') as f:
                            chapter_data = json.load(f)
                            chapters.append(chapter_data)
                    except Exception as e:
                        logger.error(f"读取章节文件失败 {chapter_file}: {e}")
            
            # 按章节号排序
            chapters.sort(key=lambda x: x.get("chapter_number", 0))
            return chapters
            
        except Exception as e:
            logger.error(f"获取章节列表失败: {e}")
            return []
    
    def save_chapter_txt(self, novel_id: str, chapter_number: int, chapter_content: Dict[str, Any]) -> str:
        """保存章节为TXT文件"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                return ""
            
            # 创建章节文件夹
            chapters_dir = os.path.join(novel_dir, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)
            
            # 获取章节标题和内容
            title = chapter_content.get("title", f"第{chapter_number}章")
            content = chapter_content.get("content", "")
            
            # 保存TXT文件
            txt_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.txt")
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n")
                f.write("=" * len(title) + "\n\n")
                f.write(content)
            
            return txt_file
        except Exception as e:
            logger.error(f"保存章节TXT文件失败: {e}")
            return ""
    
    def create_knowledge_graph(self, novel_id: str, characters: Dict[str, Any], storyline: Dict[str, Any]) -> str:
        """创建知识图谱"""
        kg_id = str(uuid.uuid4())
        
        # 构建实体
        entities = self._extract_entities(characters, storyline)
        
        # 构建关系
        relations = self._extract_relations(characters, storyline)
        
        # 构建知识图谱
        knowledge_graph = {
            "kg_id": kg_id,
            "novel_id": novel_id,
            "created_at": datetime.now().isoformat(),
            "entities": entities,
            "relations": relations,
            "properties": self._extract_properties(characters, storyline)
        }
        
        # 保存知识图谱
        kg_file = os.path.join(self.knowledge_graphs_dir, f"{kg_id}.json")
        with open(kg_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_graph, f, ensure_ascii=False, indent=2)
        
        return kg_id
    
    def update_knowledge_graph(self, kg_id: str, new_data: Dict[str, Any]) -> bool:
        """更新知识图谱"""
        try:
            kg_file = os.path.join(self.knowledge_graphs_dir, f"{kg_id}.json")
            
            if not os.path.exists(kg_file):
                return False
            
            # 加载现有知识图谱
            with open(kg_file, 'r', encoding='utf-8') as f:
                kg = json.load(f)
            
            # 更新数据
            kg["updated_at"] = datetime.now().isoformat()
            kg.update(new_data)
            
            # 保存更新后的知识图谱
            with open(kg_file, 'w', encoding='utf-8') as f:
                json.dump(kg, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"更新知识图谱失败: {e}")
            return False
    
    def get_knowledge_graph_by_novel_id(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """根据小说ID获取知识图谱"""
        try:
            # 遍历知识图谱目录，查找匹配的知识图谱
            for filename in os.listdir(self.knowledge_graphs_dir):
                if filename.endswith('.json'):
                    kg_file = os.path.join(self.knowledge_graphs_dir, filename)
                    with open(kg_file, 'r', encoding='utf-8') as f:
                        kg = json.load(f)
                        if kg.get('novel_id') == novel_id:
                            return kg
            return None
        except Exception as e:
            logger.error(f"获取知识图谱失败: {e}")
            return None
    
    def get_all_knowledge_graphs(self) -> List[Dict[str, Any]]:
        """获取所有知识图谱"""
        try:
            knowledge_graphs = []
            if not os.path.exists(self.knowledge_graphs_dir):
                return knowledge_graphs
            
            for filename in os.listdir(self.knowledge_graphs_dir):
                if filename.endswith('.json'):
                    kg_file = os.path.join(self.knowledge_graphs_dir, filename)
                    try:
                        with open(kg_file, 'r', encoding='utf-8') as f:
                            kg = json.load(f)
                            kg['id'] = filename.replace('.json', '')
                            knowledge_graphs.append(kg)
                    except Exception as e:
                        logger.error(f"读取知识图谱文件失败 {kg_file}: {e}")
            
            return knowledge_graphs
        except Exception as e:
            logger.error(f"获取知识图谱列表失败: {e}")
            return []
    
    def get_novel_list(self) -> List[Dict[str, Any]]:
        """获取小说列表"""
        novels = []
        
        for novel_id in os.listdir(self.novels_dir):
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if os.path.isdir(novel_dir):
                metadata_file = os.path.join(novel_dir, "metadata.json")
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        novels.append(metadata)
                    except Exception as e:
                        logger.error(f"读取小说元数据失败 {novel_id}: {e}")
        
        return novels
    
    def _fix_json_format(self, json_str: str) -> str:
        """修复常见的JSON格式问题 - 使用统一的JsonFixer"""
        return JsonFixer.fix_json_format(json_str, verbose=False)
    
    def _standardize_data_format(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """标准化数据格式，确保没有嵌套的JSON字符串"""
        if data_type == "characters":
            return self._standardize_character_data(data)
        elif data_type == "storyline":
            return self._standardize_storyline_data(data)
        elif data_type.startswith("chapter_"):
            return self._standardize_chapter_data(data)
        else:
            return data
    
    def _standardize_character_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化角色数据格式"""
        standardized_data = data.copy()
        
        # 处理顶层content字段
        if "content" in standardized_data and isinstance(standardized_data["content"], str):
            logger.info("发现顶层content字段，尝试解析...")
            parsed_data = self._parse_agent_output(standardized_data["content"])
            if parsed_data:
                logger.info("✓ 成功解析顶层content字段")
                # 用解析后的数据替换整个数据结构
                standardized_data = parsed_data
            else:
                logger.error("✗ 解析顶层content字段失败，保留原始数据")
                # 删除content字段，保留其他数据
                del standardized_data["content"]
        
        # 处理主角数据
        if "main_character" in standardized_data:
            main_char = standardized_data["main_character"]
            
            # 如果存在content字段，尝试解析并合并
            if "content" in main_char and isinstance(main_char["content"], str):
                parsed_data = self._parse_agent_output(main_char["content"])
                if parsed_data:
                    # 合并解析后的数据
                    for key, value in parsed_data.items():
                        main_char[key] = value
                    # 删除content字段
                    del main_char["content"]
        
        # 处理配角数据
        if "supporting_characters" in standardized_data:
            for char in standardized_data["supporting_characters"]:
                if "content" in char and isinstance(char["content"], str):
                    parsed_data = self._parse_agent_output(char["content"])
                    if parsed_data:
                        # 合并解析后的数据
                        for key, value in parsed_data.items():
                            char[key] = value
                        # 删除content字段
                        del char["content"]
        
        return standardized_data
    
    def _standardize_storyline_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化故事线数据格式"""
        standardized_data = data.copy()
        
        # 处理first_module字段
        if "first_module" in standardized_data:
            first_module = standardized_data["first_module"]
            
            if "content" in first_module and isinstance(first_module["content"], str):
                parsed_data = self._parse_agent_output(first_module["content"])
                if parsed_data:
                    # 合并解析后的数据
                    for key, value in parsed_data.items():
                        first_module[key] = value
                    # 删除content字段
                    del first_module["content"]
        
        return standardized_data
    
    def _standardize_chapter_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化章节数据格式"""
        standardized_data = data.copy()
        
        if "content" in standardized_data and isinstance(standardized_data["content"], str):
            parsed_data = self._parse_agent_output(standardized_data["content"])
            if parsed_data:
                # 合并解析后的数据
                for key, value in parsed_data.items():
                    standardized_data[key] = value
                # 删除content字段
                del standardized_data["content"]
        
        return standardized_data
    
    def _parse_agent_output(self, content: str) -> Optional[Dict[str, Any]]:
        """解析智能体输出，提取结构化数据"""
        try:
            # 如果包含markdown代码块，提取JSON部分
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    json_str = content[start:end].strip()
                    # 修复常见的JSON格式问题
                    json_str = self._fix_json_format(json_str)
                    return json.loads(json_str)
            
            # 如果没有markdown代码块，直接尝试解析
            content = self._fix_json_format(content)
            return json.loads(content)
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析智能体输出失败: {e}")
            # 如果解析失败，尝试更宽松的解析方法
            return self._parse_agent_output_fallback(content)
    
    def _parse_agent_output_fallback(self, content: str) -> Optional[Dict[str, Any]]:
        """备用解析方法，使用更宽松的规则"""
        try:
            # 尝试找到第一个完整的JSON对象
            start = content.find('{')
            if start == -1:
                return None
            
            # 找到匹配的结束括号
            brace_count = 0
            end = start
            for i in range(start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
            
            if brace_count != 0:
                # 如果找不到完整的JSON，尝试截取到最后一个完整的对象
                last_brace = content.rfind('}')
                if last_brace > start:
                    end = last_brace
                else:
                    return None
            
            json_str = content[start:end+1]
            
            # 使用统一的JSON修复方法
            try:
                fixed_json = self._fix_json_format(json_str)
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"备用解析方法也失败: {e}")
            return None
    
    def _clean_data_format(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """清理和标准化数据格式（用于修复现有数据）"""
        # 使用新的标准化方法
        return self._standardize_data_format(data, data_type)
    
    
    def _update_metadata(self, novel_id: str, data_type: str, data: Dict[str, Any]):
        """更新元数据"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            metadata_file = os.path.join(novel_dir, "metadata.json")
            
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata[data_type] = data
                metadata["updated_at"] = datetime.now().isoformat()
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"更新元数据失败: {e}")
    
    def _update_chapter_list(self, novel_id: str, chapter_number: int, chapter_content: Dict[str, Any]) -> bool:
        """更新章节列表"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            metadata_file = os.path.join(novel_dir, "metadata.json")
            
            if not os.path.exists(metadata_file):
                logger.info(f"元数据文件不存在: {metadata_file}")
                return False
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 更新或添加章节信息
            chapter_info = {
                "chapter_number": chapter_number,
                "title": chapter_content.get("title", f"第{chapter_number}章"),
                "created_at": datetime.now().isoformat(),
                "word_count": len(chapter_content.get('content', ''))
            }
            
            # 查找是否已存在该章节
            chapters = metadata.get("chapters", [])
            existing_chapter = None
            for i, chapter in enumerate(chapters):
                if chapter.get("chapter_number") == chapter_number:
                    existing_chapter = i
                    break
            
            if existing_chapter is not None:
                chapters[existing_chapter] = chapter_info
                logger.info(f"更新章节{chapter_number}信息")
            else:
                chapters.append(chapter_info)
                logger.info(f"添加章节{chapter_number}信息")
            
            metadata["chapters"] = chapters
            metadata["updated_at"] = datetime.now().isoformat()
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"元数据更新成功，当前章节数: {len(chapters)}")
            return True
            
        except Exception as e:
            logger.error(f"更新章节列表失败: {e}")
            return False
    
    def _extract_entities(self, characters: Dict[str, Any], storyline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取实体"""
        entities = []
        
        # 提取人物实体
        main_character = characters.get("main_character", {})
        if main_character:
            basic_info = main_character.get("basic_info", {})
            entities.append({
                "id": basic_info.get("name", "主角"),
                "type": "人物",
                "attributes": {
                    "name": basic_info.get("name", "主角"),
                    "age": basic_info.get("age", "未知"),
                    "occupation": basic_info.get("occupation", "未知"),
                    "role": "主角"
                }
            })
        
        # 提取配角实体
        supporting_characters = characters.get("supporting_characters", [])
        for char in supporting_characters:
            basic_info = char.get("basic_info", {})
            entities.append({
                "id": basic_info.get("name", "配角"),
                "type": "人物",
                "attributes": {
                    "name": basic_info.get("name", "配角"),
                    "age": basic_info.get("age", "未知"),
                    "occupation": basic_info.get("occupation", "未知"),
                    "role": char.get("role", "配角")
                }
            })
        
        # 提取地点实体
        world_setting = storyline.get("world_setting", "")
        if world_setting:
            entities.append({
                "id": "主要场景",
                "type": "地点",
                "attributes": {
                    "name": "主要场景",
                    "description": world_setting
                }
            })
        
        return entities
    
    def _extract_relations(self, characters: Dict[str, Any], storyline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取关系"""
        relations = []
        
        # 提取人物关系
        main_character = characters.get("main_character", {})
        main_name = main_character.get("basic_info", {}).get("name", "主角")
        
        supporting_characters = characters.get("supporting_characters", [])
        for char in supporting_characters:
            char_name = char.get("basic_info", {}).get("name", "配角")
            relationship = char.get("relationship_with_main", "未知关系")
            
            relations.append({
                "source": main_name,
                "target": char_name,
                "relation_type": relationship
            })
        
        # 提取人物与目标的关系
        main_goal = storyline.get("main_goal", "")
        if main_goal:
            relations.append({
                "source": main_name,
                "target": "故事目标",
                "relation_type": "追求"
            })
        
        return relations
    
    def _extract_properties(self, characters: Dict[str, Any], storyline: Dict[str, Any]) -> Dict[str, Any]:
        """提取属性"""
        return {
            "story_themes": storyline.get("themes", []),
            "story_tone": storyline.get("tone", ""),
            "main_conflict": storyline.get("conflict", ""),
            "world_setting": storyline.get("world_setting", "")
        }
    
    # ==================== 续写相关功能 ====================
    
    def get_novel_by_id_or_title(self, identifier: str) -> Optional[Dict[str, Any]]:
        """通过ID或标题查找小说"""
        try:
            # 首先尝试通过ID直接查找
            novel_dir = os.path.join(self.novels_dir, identifier)
            if os.path.exists(novel_dir):
                return self._load_novel_metadata(identifier)
            
            # 如果直接查找失败，尝试通过标题查找
            novels = self.get_novel_list()
            for novel in novels:
                if novel.get("title") == identifier or novel.get("novel_id") == identifier:
                    return novel
            
            return None
        except Exception as e:
            logger.error(f"查找小说失败: {e}")
            return None
    
    def _load_novel_metadata(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """加载小说元数据"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            metadata_file = os.path.join(novel_dir, "metadata.json")
            
            if not os.path.exists(metadata_file):
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载小说元数据失败: {e}")
            return None
    
    def get_novel_chapters(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取小说的所有章节（别名，调用get_chapters）"""
        return self.get_chapters(novel_id)
    
    def repair_existing_data(self, novel_id: str) -> bool:
        """修复现有数据格式问题"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                return False
            
            repaired = False
            
            # 修复角色数据
            characters_file = os.path.join(novel_dir, "characters.json")
            if os.path.exists(characters_file):
                with open(characters_file, 'r', encoding='utf-8') as f:
                    characters_data = json.load(f)
                
                cleaned_characters = self._clean_character_data(characters_data)
                if cleaned_characters != characters_data:
                    with open(characters_file, 'w', encoding='utf-8') as f:
                        json.dump(cleaned_characters, f, ensure_ascii=False, indent=2)
                    repaired = True
                    logger.info(f"修复了小说 {novel_id} 的角色数据格式")
            
            # 修复故事线数据
            storyline_file = os.path.join(novel_dir, "storyline.json")
            if os.path.exists(storyline_file):
                with open(storyline_file, 'r', encoding='utf-8') as f:
                    storyline_data = json.load(f)
                
                cleaned_storyline = self._clean_storyline_data(storyline_data)
                if cleaned_storyline != storyline_data:
                    with open(storyline_file, 'w', encoding='utf-8') as f:
                        json.dump(cleaned_storyline, f, ensure_ascii=False, indent=2)
                    repaired = True
                    logger.info(f"修复了小说 {novel_id} 的故事线数据格式")
            
            # 修复章节数据
            for filename in os.listdir(novel_dir):
                if filename.startswith("chapter_") and filename.endswith(".json"):
                    chapter_file = os.path.join(novel_dir, filename)
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                    
                    cleaned_chapter = self._clean_chapter_data(chapter_data)
                    if cleaned_chapter != chapter_data:
                        with open(chapter_file, 'w', encoding='utf-8') as f:
                            json.dump(cleaned_chapter, f, ensure_ascii=False, indent=2)
                        repaired = True
                        logger.info(f"修复了小说 {novel_id} 的章节数据格式: {filename}")
            
            return repaired
        except Exception as e:
            logger.error(f"修复数据失败: {e}")
            return False
    
    def repair_all_novels(self) -> int:
        """修复所有小说的数据格式"""
        repaired_count = 0
        novels = self.get_novel_list()
        
        for novel in novels:
            novel_id = novel["novel_id"]
            if self.repair_existing_data(novel_id):
                repaired_count += 1
        
        logger.info(f"总共修复了 {repaired_count} 个小说的数据格式")
        return repaired_count
    
    def get_novel_knowledge_base(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """获取小说的知识库"""
        try:
            # 加载小说数据
            metadata = self._load_novel_metadata(novel_id)
            if not metadata:
                return None
            
            chapters = self.get_novel_chapters(novel_id)
            characters = self.load_novel_data(novel_id, "characters") or {}
            storyline = self.load_novel_data(novel_id, "storyline") or {}
            tags = self.load_novel_data(novel_id, "tags") or {}
            
            # 构建知识库
            knowledge_base = {
                "novel_info": {
                    "novel_id": novel_id,
                    "title": metadata.get("title", "未知标题"),
                    "author": "用户",
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at"),
                    "status": metadata.get("status", "未知状态")
                },
                "chapters": chapters,
                "character_profiles": characters,
                "storyline": storyline,
                "tags": tags,
                "world_setting": storyline.get("world_setting", ""),
                "story_tone": storyline.get("tone", ""),
                "last_chapter_summary": self._get_last_chapter_summary(chapters)
            }
            
            return knowledge_base
        except Exception as e:
            logger.error(f"构建知识库失败: {e}")
            return None
    
    def _get_last_chapter_summary(self, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取最后一章的摘要"""
        if not chapters:
            return {}
        
        last_chapter = chapters[-1]
        return {
            "chapter_number": last_chapter.get("chapter_number", 0),
            "title": last_chapter.get("title", ""),
            "summary": last_chapter.get("summary", ""),
            "key_events": last_chapter.get("key_events", []),
            "foreshadowing": last_chapter.get("foreshadowing", []),
            "next_chapter_hint": last_chapter.get("next_chapter_hint", "")
        }
    
    def update_novel_status(self, novel_id: str, status: str) -> bool:
        """更新小说状态"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            metadata_file = os.path.join(novel_dir, "metadata.json")
            
            if not os.path.exists(metadata_file):
                return False
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata["status"] = status
            metadata["updated_at"] = datetime.now().isoformat()
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"更新小说状态失败: {e}")
            return False
    
    def get_novel_statistics(self, novel_id: str) -> Dict[str, Any]:
        """获取小说统计信息"""
        try:
            chapters = self.get_novel_chapters(novel_id)
            metadata = self._load_novel_metadata(novel_id)
            
            if not metadata:
                return {}
            
            # 计算总字数
            total_word_count = 0
            for chapter in chapters:
                content = chapter.get("content", "")
                total_word_count += len(content)
            
            # 计算平均章节长度
            avg_chapter_length = total_word_count / len(chapters) if chapters else 0
            
            return {
                "novel_id": novel_id,
                "title": metadata.get("title", "未知标题"),
                "chapter_count": len(chapters),
                "total_word_count": total_word_count,
                "avg_chapter_length": round(avg_chapter_length, 2),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "status": metadata.get("status", "未知状态")
            }
        except Exception as e:
            logger.error(f"获取小说统计信息失败: {e}")
            return {}
    
    def delete_chapter(self, novel_id: str, chapter_number: int) -> bool:
        """删除指定章节"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                logger.info(f"小说目录不存在: {novel_dir}")
                return False
            
            # 删除章节JSON文件
            chapter_file = os.path.join(novel_dir, f"chapter_{chapter_number:03d}.json")
            if os.path.exists(chapter_file):
                os.remove(chapter_file)
                logger.info(f"已删除章节JSON文件: {chapter_file}")
            
            # 删除章节TXT文件
            chapters_dir = os.path.join(novel_dir, "chapters")
            txt_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.txt")
            if os.path.exists(txt_file):
                os.remove(txt_file)
                logger.info(f"已删除章节TXT文件: {txt_file}")
            
            # 更新元数据中的章节列表
            self._remove_chapter_from_metadata(novel_id, chapter_number)
            
            logger.info(f"章节{chapter_number}删除完成")
            return True
            
        except Exception as e:
            logger.error(f"删除章节失败: {e}")
            return False
    
    def delete_novel(self, novel_id: str) -> bool:
        """删除整个小说项目"""
        try:
            novel_dir = os.path.join(self.novels_dir, novel_id)
            if not os.path.exists(novel_dir):
                logger.info(f"小说目录不存在: {novel_dir}")
                return False
            
            import shutil
            shutil.rmtree(novel_dir)
            logger.info(f"已删除小说目录: {novel_dir}")
            
            # 删除知识图谱文件（如果存在）
            knowledge_graphs = self.get_all_knowledge_graphs()
            for kg in knowledge_graphs:
                if kg.get("novel_id") == novel_id:
                    kg_file = os.path.join(self.knowledge_graphs_dir, f"{kg['id']}.json")
                    if os.path.exists(kg_file):
                        os.remove(kg_file)
                        logger.info(f"已删除知识图谱文件: {kg_file}")
            
            # 删除快速续写状态文件（如果存在）
            quick_status_dir = os.path.join(self.novels_dir, "quick_continuation_status")
            quick_status_file = os.path.join(quick_status_dir, f"{novel_id}.json")
            if os.path.exists(quick_status_file):
                os.remove(quick_status_file)
                logger.info(f"已删除快速续写状态文件: {quick_status_file}")
            
            logger.info(f"小说 {novel_id} 删除完成")
            return True
            
        except Exception as e:
            logger.error(f"删除小说失败: {e}")
            return False
    
    def _remove_chapter_from_metadata(self, novel_id: str, chapter_number: int) -> bool:
        """从元数据中移除章节信息"""
        try:
            metadata = self._load_novel_metadata(novel_id)
            if not metadata:
                return False
            
            # 移除指定章节
            if "chapters" in metadata:
                metadata["chapters"] = [
                    ch for ch in metadata["chapters"] 
                    if ch.get("chapter_number") != chapter_number
                ]
                
                # 重新排序剩余章节的编号
                for i, chapter in enumerate(metadata["chapters"]):
                    if chapter.get("chapter_number", 0) > chapter_number:
                        chapter["chapter_number"] = chapter["chapter_number"] - 1
            
            # 更新时间戳
            metadata["updated_at"] = datetime.now().isoformat()
            
            # 保存更新后的元数据
            metadata_file = os.path.join(self.novels_dir, novel_id, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已从元数据中移除章节{chapter_number}")
            return True
            
        except Exception as e:
            logger.error(f"更新元数据失败: {e}")
            return False