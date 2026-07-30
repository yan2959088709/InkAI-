"""
长期一致性保证系统
负责保证长期续写的一致性和质量
"""

import time
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import threading
from utils.logger import get_logger
logger = get_logger("long_term_consistency_system")


class LongTermConsistencySystem:
    """长期一致性保证系统"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.consistency_cache = {}
        self.consistency_lock = threading.Lock()
        self.consistency_rules = {}
        self.consistency_history = []
    
    def initialize_consistency_rules(self, novel_id: str, novel_data: Dict[str, Any]) -> bool:
        """初始化一致性规则"""
        try:
            # 从小说数据中提取一致性规则
            consistency_rules = {
                "novel_id": novel_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "character_consistency_rules": self._extract_character_rules(novel_data),
                "world_consistency_rules": self._extract_world_rules(novel_data),
                "plot_consistency_rules": self._extract_plot_rules(novel_data),
                "style_consistency_rules": self._extract_style_rules(novel_data),
                "theme_consistency_rules": self._extract_theme_rules(novel_data)
            }
            
            # 缓存一致性规则
            with self.consistency_lock:
                self.consistency_rules[novel_id] = consistency_rules
            
            # 保存到文件
            self._save_consistency_rules(novel_id, consistency_rules)
            
            return True
            
        except Exception as e:
            logger.error(f"初始化一致性规则失败: {e}")
            return False
    
    def check_character_consistency(self, novel_id: str, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """检查人物一致性"""
        try:
            character_rules = self._get_character_rules(novel_id)
            if not character_rules:
                return {"consistent": True, "issues": []}
            
            issues = []
            
            # 检查主角一致性
            main_character_issues = self._check_main_character_consistency(
                chapter_content, character_rules.get("main_character", {})
            )
            issues.extend(main_character_issues)
            
            # 检查配角一致性
            supporting_character_issues = self._check_supporting_character_consistency(
                chapter_content, character_rules.get("supporting_characters", [])
            )
            issues.extend(supporting_character_issues)
            
            # 检查人物关系一致性
            relationship_issues = self._check_character_relationship_consistency(
                chapter_content, character_rules.get("relationships", {})
            )
            issues.extend(relationship_issues)
            
            return {
                "consistent": len(issues) == 0,
                "issues": issues,
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"检查人物一致性失败: {e}")
            return {"consistent": False, "issues": [f"检查过程出错: {str(e)}"]}
    
    def check_world_consistency(self, novel_id: str, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """检查世界观一致性"""
        try:
            world_rules = self._get_world_rules(novel_id)
            if not world_rules:
                return {"consistent": True, "issues": []}
            
            issues = []
            
            # 检查世界规则一致性
            world_rule_issues = self._check_world_rule_consistency(
                chapter_content, world_rules.get("world_rules", {})
            )
            issues.extend(world_rule_issues)
            
            # 检查地理环境一致性
            geographical_issues = self._check_geographical_consistency(
                chapter_content, world_rules.get("geographical", {})
            )
            issues.extend(geographical_issues)
            
            # 检查社会制度一致性
            social_issues = self._check_social_consistency(
                chapter_content, world_rules.get("social", {})
            )
            issues.extend(social_issues)
            
            return {
                "consistent": len(issues) == 0,
                "issues": issues,
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"检查世界观一致性失败: {e}")
            return {"consistent": False, "issues": [f"检查过程出错: {str(e)}"]}
    
    def check_plot_consistency(self, novel_id: str, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """检查情节一致性"""
        try:
            plot_rules = self._get_plot_rules(novel_id)
            if not plot_rules:
                return {"consistent": True, "issues": []}
            
            issues = []
            
            # 检查主线一致性
            main_plot_issues = self._check_main_plot_consistency(
                chapter_content, plot_rules.get("main_plot", [])
            )
            issues.extend(main_plot_issues)
            
            # 检查支线一致性
            sub_plot_issues = self._check_sub_plot_consistency(
                chapter_content, plot_rules.get("sub_plots", [])
            )
            issues.extend(sub_plot_issues)
            
            # 检查伏笔一致性
            foreshadowing_issues = self._check_foreshadowing_consistency(
                chapter_content, plot_rules.get("foreshadowing", [])
            )
            issues.extend(foreshadowing_issues)
            
            return {
                "consistent": len(issues) == 0,
                "issues": issues,
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"检查情节一致性失败: {e}")
            return {"consistent": False, "issues": [f"检查过程出错: {str(e)}"]}
    
    def check_style_consistency(self, novel_id: str, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """检查风格一致性"""
        try:
            style_rules = self._get_style_rules(novel_id)
            if not style_rules:
                return {"consistent": True, "issues": []}
            
            issues = []
            
            # 检查语言风格一致性
            language_issues = self._check_language_style_consistency(
                chapter_content, style_rules.get("language_style", {})
            )
            issues.extend(language_issues)
            
            # 检查叙事风格一致性
            narrative_issues = self._check_narrative_style_consistency(
                chapter_content, style_rules.get("narrative_style", {})
            )
            issues.extend(narrative_issues)
            
            # 检查情感风格一致性
            emotional_issues = self._check_emotional_style_consistency(
                chapter_content, style_rules.get("emotional_style", {})
            )
            issues.extend(emotional_issues)
            
            return {
                "consistent": len(issues) == 0,
                "issues": issues,
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"检查风格一致性失败: {e}")
            return {"consistent": False, "issues": [f"检查过程出错: {str(e)}"]}
    
    def check_theme_consistency(self, novel_id: str, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """检查主题一致性"""
        try:
            theme_rules = self._get_theme_rules(novel_id)
            if not theme_rules:
                return {"consistent": True, "issues": []}
            
            issues = []
            
            # 检查主要主题一致性
            main_theme_issues = self._check_main_theme_consistency(
                chapter_content, theme_rules.get("main_themes", [])
            )
            issues.extend(main_theme_issues)
            
            # 检查次要主题一致性
            sub_theme_issues = self._check_sub_theme_consistency(
                chapter_content, theme_rules.get("sub_themes", [])
            )
            issues.extend(sub_theme_issues)
            
            # 检查主题发展一致性
            theme_development_issues = self._check_theme_development_consistency(
                chapter_content, theme_rules.get("theme_development", {})
            )
            issues.extend(theme_development_issues)
            
            return {
                "consistent": len(issues) == 0,
                "issues": issues,
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"检查主题一致性失败: {e}")
            return {"consistent": False, "issues": [f"检查过程出错: {str(e)}"]}
    
    def comprehensive_consistency_check(self, novel_id: str, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """综合一致性检查"""
        try:
            # 执行所有一致性检查
            character_check = self.check_character_consistency(novel_id, chapter_content)
            world_check = self.check_world_consistency(novel_id, chapter_content)
            plot_check = self.check_plot_consistency(novel_id, chapter_content)
            style_check = self.check_style_consistency(novel_id, chapter_content)
            theme_check = self.check_theme_consistency(novel_id, chapter_content)
            
            # 汇总结果
            all_issues = []
            all_issues.extend(character_check.get("issues", []))
            all_issues.extend(world_check.get("issues", []))
            all_issues.extend(plot_check.get("issues", []))
            all_issues.extend(style_check.get("issues", []))
            all_issues.extend(theme_check.get("issues", []))
            
            # 计算一致性分数
            consistency_score = self._calculate_consistency_score(
                character_check, world_check, plot_check, style_check, theme_check
            )
            
            # 记录检查历史
            self._record_consistency_check(novel_id, {
                "chapter_content": chapter_content,
                "character_check": character_check,
                "world_check": world_check,
                "plot_check": plot_check,
                "style_check": style_check,
                "theme_check": theme_check,
                "consistency_score": consistency_score,
                "check_time": datetime.now().isoformat()
            })
            
            return {
                "consistent": len(all_issues) == 0,
                "consistency_score": consistency_score,
                "total_issues": len(all_issues),
                "issues": all_issues,
                "detailed_checks": {
                    "character": character_check,
                    "world": world_check,
                    "plot": plot_check,
                    "style": style_check,
                    "theme": theme_check
                },
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"综合一致性检查失败: {e}")
            return {"consistent": False, "issues": [f"检查过程出错: {str(e)}"]}
    
    def _extract_character_rules(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取人物一致性规则"""
        try:
            characters = novel_data.get("characters", {})
            main_character = characters.get("main_character", {})
            supporting_characters = characters.get("supporting_characters", [])
            
            return {
                "main_character": {
                    "name": main_character.get("basic_info", {}).get("name", ""),
                    "personality": main_character.get("personality", {}),
                    "background": main_character.get("background", {}),
                    "skills": main_character.get("skills", [])
                },
                "supporting_characters": [
                    {
                        "name": char.get("basic_info", {}).get("name", ""),
                        "role": char.get("role", ""),
                        "personality": char.get("personality", ""),
                        "relationship_with_main": char.get("relationship_with_main", "")
                    }
                    for char in supporting_characters
                ],
                "relationships": characters.get("character_relationships", {})
            }
        except Exception as e:
            logger.error(f"提取人物规则失败: {e}")
            return {}
    
    def _extract_world_rules(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取世界观一致性规则"""
        try:
            storyline = novel_data.get("storyline", {})
            overall_storyline = storyline.get("overall_storyline", {})
            world_setting = overall_storyline.get("world_setting", {})
            
            return {
                "world_rules": world_setting.get("rules", {}),
                "geographical": world_setting.get("geographical", {}),
                "social": world_setting.get("social", {}),
                "cultural": world_setting.get("cultural", {})
            }
        except Exception as e:
            logger.error(f"提取世界观规则失败: {e}")
            return {}
    
    def _extract_plot_rules(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取情节一致性规则"""
        try:
            storyline = novel_data.get("storyline", {})
            overall_storyline = storyline.get("overall_storyline", {})
            
            return {
                "main_plot": overall_storyline.get("main_plot", []),
                "sub_plots": overall_storyline.get("sub_plots", []),
                "foreshadowing": overall_storyline.get("foreshadowing", []),
                "plot_structure": overall_storyline.get("plot_structure", {})
            }
        except Exception as e:
            logger.error(f"提取情节规则失败: {e}")
            return {}
    
    def _extract_style_rules(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取风格一致性规则"""
        try:
            metadata = novel_data.get("metadata", {})
            
            return {
                "language_style": metadata.get("language_style", {}),
                "narrative_style": metadata.get("narrative_style", {}),
                "emotional_style": metadata.get("emotional_style", {}),
                "writing_style": metadata.get("writing_style", "")
            }
        except Exception as e:
            logger.error(f"提取风格规则失败: {e}")
            return {}
    
    def _extract_theme_rules(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取主题一致性规则"""
        try:
            storyline = novel_data.get("storyline", {})
            overall_storyline = storyline.get("overall_storyline", {})
            
            return {
                "main_themes": overall_storyline.get("themes", []),
                "sub_themes": overall_storyline.get("sub_themes", []),
                "theme_development": overall_storyline.get("theme_development", {})
            }
        except Exception as e:
            logger.error(f"提取主题规则失败: {e}")
            return {}
    
    def _calculate_consistency_score(self, *checks) -> float:
        """计算一致性分数"""
        try:
            total_score = 0
            valid_checks = 0
            
            for check in checks:
                if check.get("consistent", False):
                    total_score += 100
                else:
                    # 根据问题数量计算分数
                    issues_count = len(check.get("issues", []))
                    if issues_count == 0:
                        total_score += 100
                    elif issues_count <= 2:
                        total_score += 80
                    elif issues_count <= 5:
                        total_score += 60
                    else:
                        total_score += 40
                valid_checks += 1
            
            return total_score / valid_checks if valid_checks > 0 else 0
            
        except Exception as e:
            logger.error(f"计算一致性分数失败: {e}")
            return 0
    
    def _record_consistency_check(self, novel_id: str, check_result: Dict[str, Any]):
        """记录一致性检查结果"""
        try:
            with self.consistency_lock:
                self.consistency_history.append({
                    "novel_id": novel_id,
                    "check_result": check_result,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 保持最近1000条记录
                if len(self.consistency_history) > 1000:
                    self.consistency_history = self.consistency_history[-1000:]
                    
        except Exception as e:
            logger.error(f"记录一致性检查失败: {e}")
    
    def _save_consistency_rules(self, novel_id: str, rules: Dict[str, Any]) -> bool:
        """保存一致性规则"""
        try:
            if self.data_manager and hasattr(self.data_manager, 'novels_dir'):
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                os.makedirs(novel_dir, exist_ok=True)
                
                file_path = os.path.join(novel_dir, "consistency_rules.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(rules, f, ensure_ascii=False, indent=2)
            else:
                # 使用当前目录作为备选
                os.makedirs("consistency_rules", exist_ok=True)
                file_path = os.path.join("consistency_rules", f"{novel_id}_consistency_rules.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(rules, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存一致性规则失败: {e}")
            return False
    
    def _get_character_rules(self, novel_id: str) -> Dict[str, Any]:
        """获取人物规则"""
        with self.consistency_lock:
            return self.consistency_rules.get(novel_id, {}).get("character_consistency_rules", {})
    
    def _get_world_rules(self, novel_id: str) -> Dict[str, Any]:
        """获取世界观规则"""
        with self.consistency_lock:
            return self.consistency_rules.get(novel_id, {}).get("world_consistency_rules", {})
    
    def _get_plot_rules(self, novel_id: str) -> Dict[str, Any]:
        """获取情节规则"""
        with self.consistency_lock:
            return self.consistency_rules.get(novel_id, {}).get("plot_consistency_rules", {})
    
    def _get_style_rules(self, novel_id: str) -> Dict[str, Any]:
        """获取风格规则"""
        with self.consistency_lock:
            return self.consistency_rules.get(novel_id, {}).get("style_consistency_rules", {})
    
    def _get_theme_rules(self, novel_id: str) -> Dict[str, Any]:
        """获取主题规则"""
        with self.consistency_lock:
            return self.consistency_rules.get(novel_id, {}).get("theme_consistency_rules", {})
    
    # 各种一致性检查的具体实现方法
    def _check_main_character_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查主角一致性"""
        # 这里应该实现具体的主角一致性检查逻辑
        return []
    
    def _check_supporting_character_consistency(self, chapter_content: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[str]:
        """检查配角一致性"""
        # 这里应该实现具体的配角一致性检查逻辑
        return []
    
    def _check_character_relationship_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查人物关系一致性"""
        # 这里应该实现具体的人物关系一致性检查逻辑
        return []
    
    def _check_world_rule_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查世界规则一致性"""
        # 这里应该实现具体的世界规则一致性检查逻辑
        return []
    
    def _check_geographical_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查地理环境一致性"""
        # 这里应该实现具体的地理环境一致性检查逻辑
        return []
    
    def _check_social_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查社会制度一致性"""
        # 这里应该实现具体的社会制度一致性检查逻辑
        return []
    
    def _check_main_plot_consistency(self, chapter_content: Dict[str, Any], rules: List[str]) -> List[str]:
        """检查主线一致性"""
        # 这里应该实现具体的主线一致性检查逻辑
        return []
    
    def _check_sub_plot_consistency(self, chapter_content: Dict[str, Any], rules: List[str]) -> List[str]:
        """检查支线一致性"""
        # 这里应该实现具体的支线一致性检查逻辑
        return []
    
    def _check_foreshadowing_consistency(self, chapter_content: Dict[str, Any], rules: List[str]) -> List[str]:
        """检查伏笔一致性"""
        # 这里应该实现具体的伏笔一致性检查逻辑
        return []
    
    def _check_language_style_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查语言风格一致性"""
        # 这里应该实现具体的语言风格一致性检查逻辑
        return []
    
    def _check_narrative_style_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查叙事风格一致性"""
        # 这里应该实现具体的叙事风格一致性检查逻辑
        return []
    
    def _check_emotional_style_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查情感风格一致性"""
        # 这里应该实现具体的情感风格一致性检查逻辑
        return []
    
    def _check_main_theme_consistency(self, chapter_content: Dict[str, Any], rules: List[str]) -> List[str]:
        """检查主要主题一致性"""
        # 这里应该实现具体的主要主题一致性检查逻辑
        return []
    
    def _check_sub_theme_consistency(self, chapter_content: Dict[str, Any], rules: List[str]) -> List[str]:
        """检查次要主题一致性"""
        # 这里应该实现具体的次要主题一致性检查逻辑
        return []
    
    def _check_theme_development_consistency(self, chapter_content: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """检查主题发展一致性"""
        # 这里应该实现具体的主题发展一致性检查逻辑
        return []
