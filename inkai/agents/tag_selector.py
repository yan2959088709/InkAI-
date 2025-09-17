# 增强版标签选择智能体
# 负责根据用户需求推荐合适的小说标签

import json
import random
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.base_agent import EnhancedBaseAgent


class EnhancedTagSelectorAgent(EnhancedBaseAgent):
    """增强版标签选择智能体 - 负责根据用户需求推荐合适的小说标签"""
    
    def __init__(self):
        super().__init__("增强标签选择智能体")
        
        # 扩展的标签分类系统
        self.tag_categories = {
            "类型标签": {
                "现代": ["都市", "校园", "职场", "娱乐圈", "商战", "医疗", "律政"],
                "古代": ["历史", "宫廷", "武侠", "仙侠", "古言", "架空", "种田"],
                "奇幻": ["玄幻", "奇幻", "魔幻", "异世界", "穿越", "重生", "修仙"],
                "科幻": ["科幻", "未来", "星际", "机甲", "末世", "赛博朋克", "太空"],
                "悬疑": ["悬疑", "推理", "犯罪", "恐怖", "灵异", "惊悚", "探案"],
                "其他": ["军事", "体育", "游戏", "美食", "旅游", "音乐", "艺术"]
            },
            "主题标签": {
                "成长": ["成长", "励志", "逆袭", "奋斗", "蜕变", "自我实现"],
                "情感": ["爱情", "友情", "亲情", "师生情", "兄弟情", "暗恋", "失恋"],
                "冒险": ["冒险", "探险", "寻宝", "旅行", "挑战", "求生", "探索"],
                "权谋": ["权谋", "政治", "商战", "宫斗", "智斗", "阴谋", "策略"],
                "治愈": ["治愈", "温馨", "日常", "生活", "家庭", "美食", "田园"],
                "特殊": ["复仇", "重生", "系统", "金手指", "快穿", "无限流", "穿书"]
            },
            "风格标签": {
                "轻松": ["轻松愉快", "幽默诙谐", "搞笑", "沙雕", "甜宠", "治愈"],
                "严肃": ["严肃深刻", "文艺抒情", "哲学思辨", "现实主义", "批判"],
                "热血": ["热血激昂", "燃", "激情", "战斗", "竞技", "冒险"],
                "温馨": ["温馨治愈", "小清新", "治愈系", "温暖", "日常"],
                "黑暗": ["黑暗压抑", "虐心", "悲剧", "沉重", "现实", "残酷"]
            },
            "受众标签": {
                "年龄": ["儿童向", "青少年", "成年人", "全年龄"],
                "性别": ["女性向", "男性向", "中性向"],
                "偏好": ["小白文", "老白文", "深度文", "爽文", "文青文", "快节奏", "慢节奏"]
            }
        }
        
        # 标签权重和关联性
        self.tag_weights = {
            "类型标签": 0.4,
            "主题标签": 0.3,
            "风格标签": 0.2,
            "受众标签": 0.1
        }
        
        # 增强的标签兼容性矩阵
        self.compatibility_matrix = self._build_enhanced_compatibility_matrix()
        
        # 热门标签组合
        self.popular_combinations = self._load_popular_combinations()
        
        self._log("增强版标签选择智能体初始化完成", "INFO")
    
    def _build_enhanced_compatibility_matrix(self) -> Dict[str, Dict[str, float]]:
        """构建增强的标签兼容性矩阵"""
        return {
            "都市": {
                "职场": 0.9, "校园": 0.8, "娱乐圈": 0.7, "商战": 0.8,
                "成长": 0.8, "爱情": 0.9, "励志": 0.8, "现实主义": 0.7
            },
            "玄幻": {
                "修仙": 0.9, "异世界": 0.8, "系统": 0.7, "重生": 0.6,
                "冒险": 0.9, "热血": 0.8, "成长": 0.7, "爽文": 0.8
            },
            "悬疑": {
                "推理": 0.9, "犯罪": 0.8, "恐怖": 0.7, "灵异": 0.6,
                "智斗": 0.8, "严肃": 0.7, "成年人": 0.8
            },
            "言情": {
                "甜宠": 0.9, "虐恋": 0.7, "校园": 0.8, "职场": 0.6,
                "爱情": 0.9, "治愈": 0.7, "女性向": 0.9
            },
            "历史": {
                "宫廷": 0.9, "武侠": 0.7, "架空": 0.8,
                "权谋": 0.8, "严肃": 0.7, "文艺": 0.6
            },
            "科幻": {
                "未来": 0.9, "星际": 0.8, "机甲": 0.7,
                "探索": 0.8, "哲学": 0.6, "严肃": 0.7
            }
        }
    
    def _load_popular_combinations(self) -> List[Dict[str, Any]]:
        """加载热门标签组合"""
        return [
            {
                "name": "都市系统爽文",
                "tags": ["都市", "系统", "逆袭", "爽文"],
                "popularity": 0.9,
                "success_rate": 0.85
            },
            {
                "name": "玄幻修仙",
                "tags": ["玄幻", "修仙", "热血", "冒险"],
                "popularity": 0.95,
                "success_rate": 0.9
            },
            {
                "name": "校园甜宠",
                "tags": ["校园", "甜宠", "爱情", "治愈"],
                "popularity": 0.8,
                "success_rate": 0.8
            }
        ]
    
    def recommend_tags(self, user_requirements: str, custom_tags: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """根据用户需求推荐标签（增强版）"""
        self._log(f"开始分析用户需求: {user_requirements}", "INFO")
        
        # 构建增强的提示词
        prompt = self._build_enhanced_prompt(user_requirements)
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的小说标签推荐专家，擅长分析用户需求并推荐合适的标签组合。你了解各种小说类型的特征和受众偏好，能够基于市场趋势提供精准建议。"
            },
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 验证和优化推荐结果
        validated_result = self._validate_and_optimize_tags(result, user_requirements)
        
        # 添加热门组合建议
        validated_result = self._add_popular_combinations(validated_result, user_requirements)
        
        # 如果用户提供了自定义标签，进行合并
        if custom_tags:
            validated_result = self._merge_custom_tags(validated_result, custom_tags)
        
        self._log(f"标签推荐完成，置信度: {validated_result.get('confidence', 0)}", "INFO")
        return validated_result
    
    def _build_enhanced_prompt(self, user_requirements: str) -> str:
        """构建增强的提示词"""
        # 关键词提取
        keywords = self._extract_keywords(user_requirements)
        
        # 热门组合匹配
        matching_combinations = self._find_matching_combinations(user_requirements)
        
        prompt = f"""
        你是一个专业的小说标签推荐专家，请根据用户需求推荐最合适的小说标签组合。
        
        用户需求：{user_requirements}
        提取的关键词：{keywords}
        匹配的热门组合：{matching_combinations}
        
        可选标签分类：
        {self._format_tag_categories()}
        
        推荐原则：
        1. 根据关键词精准匹配标签
        2. 考虑标签兼容性和组合效果
        3. 参考市场热门组合
        4. 每个分类推荐2-4个最合适的标签
        5. 确保标签组合能形成完整的故事框架
        6. 考虑目标受众的喜好和市场趋势
        
        请返回JSON格式：
        {{
            "recommended_tags": {{
                "类型标签": ["推荐的类型标签"],
                "主题标签": ["推荐的主题标签"], 
                "风格标签": ["推荐的风格标签"],
                "受众标签": ["推荐的受众标签"]
            }},
            "reasoning": "详细的推荐理由和标签组合说明",
            "confidence": 0.85,
            "market_potential": "市场潜力评估",
            "target_audience": "目标受众分析",
            "alternative_tags": {{
                "类型标签": ["备选类型标签"],
                "主题标签": ["备选主题标签"]
            }}
        }}
        """
        return prompt
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 类型关键词
        type_keywords = {
            "都市": ["都市", "现代", "城市", "白领", "职场"],
            "玄幻": ["玄幻", "修仙", "法术", "灵气", "境界"],
            "科幻": ["科幻", "未来", "机器人", "太空", "星际"],
            "历史": ["古代", "历史", "朝代", "皇帝", "大臣"]
        }
        
        for tag_type, words in type_keywords.items():
            if any(word in text for word in words):
                keywords.append(tag_type)
        
        return keywords
    
    def _find_matching_combinations(self, requirements: str) -> List[Dict[str, Any]]:
        """查找匹配的热门组合"""
        matching = []
        
        for combo in self.popular_combinations:
            # 检查是否包含组合中的关键词
            if any(tag in requirements for tag in combo["tags"]):
                matching.append(combo)
        
        return matching
    
    def _format_tag_categories(self) -> str:
        """格式化标签分类"""
        formatted = ""
        for category, subcategories in self.tag_categories.items():
            formatted += f"{category}:\n"
            for subcat, tags in subcategories.items():
                formatted += f"  {subcat}: {', '.join(tags)}\n"
            formatted += "\n"
        return formatted
    
    def _validate_and_optimize_tags(self, result: Dict[str, Any], requirements: str) -> Dict[str, Any]:
        """验证和优化标签推荐（增强版）"""
        validated = {
            "recommended_tags": {},
            "reasoning": result.get("reasoning", "基于用户需求和市场分析推荐"),
            "confidence": result.get("confidence", 0.8),
            "market_potential": result.get("market_potential", "待评估"),
            "target_audience": result.get("target_audience", "待分析"),
            "alternative_tags": result.get("alternative_tags", {}),
            "validation_notes": [],
            "optimization_applied": []
        }
        
        # 验证每个分类的标签
        for category in ["类型标签", "主题标签", "风格标签", "受众标签"]:
            recommended = result.get("recommended_tags", {}).get(category, [])
            valid_tags = self._validate_category_tags(category, recommended)
            
            # 如果没有有效标签，使用智能推荐
            if not valid_tags:
                valid_tags = self._smart_recommend_for_category(category, requirements)
                validated["optimization_applied"].append(f"{category}使用智能推荐")
            
            validated["recommended_tags"][category] = valid_tags
        
        # 检查标签兼容性
        compatibility_score = self._calculate_enhanced_compatibility_score(validated["recommended_tags"])
        validated["compatibility_score"] = compatibility_score
        
        if compatibility_score < 0.6:
            # 自动优化兼容性
            optimized_tags = self._optimize_compatibility(validated["recommended_tags"])
            validated["recommended_tags"] = optimized_tags
            validated["optimization_applied"].append("兼容性优化")
        
        # 市场潜力评估
        market_score = self._evaluate_market_potential(validated["recommended_tags"])
        validated["market_score"] = market_score
        
        return validated
    
    def _validate_category_tags(self, category: str, recommended: List[str]) -> List[str]:
        """验证分类标签"""
        valid_tags = []
        
        if category in self.tag_categories:
            # 在所有子分类中查找有效标签
            for subcat, tags in self.tag_categories[category].items():
                for tag in recommended:
                    if tag in tags and tag not in valid_tags:
                        valid_tags.append(tag)
        
        return valid_tags
    
    def _smart_recommend_for_category(self, category: str, requirements: str) -> List[str]:
        """智能推荐分类标签"""
        # 基于关键词的智能推荐
        if "都市" in requirements or "现代" in requirements:
            if category == "类型标签":
                return ["都市"]
            elif category == "主题标签":
                return ["成长", "爱情"]
        elif "古代" in requirements or "历史" in requirements:
            if category == "类型标签":
                return ["历史", "武侠"]
            elif category == "主题标签":
                return ["权谋", "冒险"]
        
        # 默认推荐
        defaults = {
            "类型标签": ["都市", "奇幻"],
            "主题标签": ["成长", "冒险"],
            "风格标签": ["轻松愉快"],
            "受众标签": ["全年龄"]
        }
        
        return defaults.get(category, ["未知"])
    
    def _calculate_enhanced_compatibility_score(self, tags: Dict[str, List[str]]) -> float:
        """计算增强的标签兼容性得分"""
        if not tags:
            return 0.0
        
        total_score = 0.0
        count = 0
        
        # 检查类型标签与其他标签的兼容性
        type_tags = tags.get("类型标签", [])
        
        for type_tag in type_tags:
            if type_tag in self.compatibility_matrix:
                compatibility_data = self.compatibility_matrix[type_tag]
                
                # 检查与所有其他标签的兼容性
                for other_category, other_tags in tags.items():
                    if other_category != "类型标签":
                        for other_tag in other_tags:
                            if other_tag in compatibility_data:
                                total_score += compatibility_data[other_tag]
                                count += 1
        
        return total_score / max(count, 1)
    
    def _optimize_compatibility(self, tags: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """优化标签兼容性"""
        # 简单的兼容性优化策略
        optimized = tags.copy()
        
        # 如果有都市标签，优化其他标签
        if "都市" in tags.get("类型标签", []):
            if "主题标签" in optimized:
                # 添加兼容的主题标签
                compatible_themes = ["成长", "爱情", "励志"]
                for theme in compatible_themes:
                    if theme not in optimized["主题标签"]:
                        optimized["主题标签"].append(theme)
                        break
        
        return optimized
    
    def _evaluate_market_potential(self, tags: Dict[str, List[str]]) -> float:
        """评估市场潜力"""
        # 基于热门组合评估市场潜力
        potential_score = 0.5  # 基础分
        
        for combo in self.popular_combinations:
            combo_tags = combo["tags"]
            all_tags = []
            for tag_list in tags.values():
                all_tags.extend(tag_list)
            
            # 计算与热门组合的匹配度
            match_count = sum(1 for tag in combo_tags if tag in all_tags)
            if match_count >= 2:
                potential_score += combo["popularity"] * 0.3
        
        return min(1.0, potential_score)
    
    def _add_popular_combinations(self, result: Dict[str, Any], requirements: str) -> Dict[str, Any]:
        """添加热门组合建议"""
        matching_combinations = self._find_matching_combinations(requirements)
        
        if matching_combinations:
            result["popular_combinations"] = matching_combinations
            result["validation_notes"].append("找到匹配的热门组合")
        
        return result
    
    def _merge_custom_tags(self, result: Dict[str, Any], custom_tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """合并自定义标签"""
        for category, tags in custom_tags.items():
            if category in result["recommended_tags"]:
                # 合并标签，去重
                existing_tags = result["recommended_tags"][category]
                merged_tags = list(set(existing_tags + tags))
                result["recommended_tags"][category] = merged_tags
        
        return result
    
    def suggest_tag_improvements(self, current_tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """建议标签改进"""
        improvements = {
            "suggestions": [],
            "missing_categories": [],
            "compatibility_issues": [],
            "market_optimization": []
        }
        
        # 检查缺失的分类
        for category in self.tag_categories.keys():
            if category not in current_tags or not current_tags[category]:
                improvements["missing_categories"].append(category)
        
        # 检查兼容性
        compatibility_score = self._calculate_enhanced_compatibility_score(current_tags)
        if compatibility_score < 0.6:
            improvements["compatibility_issues"].append(f"兼容性得分较低: {compatibility_score:.2f}")
        
        # 市场优化建议
        market_score = self._evaluate_market_potential(current_tags)
        if market_score < 0.7:
            improvements["market_optimization"].append(f"市场潜力可提升: {market_score:.2f}")
        
        return improvements
    
    def analyze_tag_trends(self, novel_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析标签趋势（增强版）"""
        if not novel_data_list:
            return {"error": "没有数据可分析"}
        
        # 统计标签使用频率
        tag_stats = self._collect_tag_statistics(novel_data_list)
        
        # 计算趋势
        trends = self._calculate_trends(tag_stats)
        
        # 生成洞察
        insights = self._generate_trend_insights(trends)
        
        # 预测热门标签
        predictions = self._predict_trending_tags(tag_stats)
        
        return {
            "tag_statistics": tag_stats,
            "trends": trends,
            "insights": insights,
            "predictions": predictions,
            "analysis_date": datetime.now().isoformat(),
            "sample_size": len(novel_data_list)
        }
    
    def _collect_tag_statistics(self, novel_data_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """收集标签统计数据"""
        tag_stats = {
            "类型标签": {},
            "主题标签": {},
            "风格标签": {},
            "受众标签": {}
        }
        
        for novel_data in novel_data_list:
            tags = novel_data.get("tags", {}).get("recommended_tags", {})
            for category, tag_list in tags.items():
                if category in tag_stats:
                    for tag in tag_list:
                        tag_stats[category][tag] = tag_stats[category].get(tag, 0) + 1
        
        return tag_stats
    
    def _calculate_trends(self, tag_stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """计算趋势"""
        trends = {}
        
        for category, stats in tag_stats.items():
            if stats:
                sorted_tags = sorted(stats.items(), key=lambda x: x[1], reverse=True)
                total_usage = sum(stats.values())
                
                trends[category] = {
                    "top_tags": sorted_tags[:5],
                    "total_unique_tags": len(stats),
                    "most_popular": sorted_tags[0][0] if sorted_tags else None,
                    "usage_distribution": [(tag, count/total_usage) for tag, count in sorted_tags[:10]],
                    "diversity_score": len(stats) / max(total_usage, 1)
                }
        
        return trends
    
    def _generate_trend_insights(self, trends: Dict[str, Any]) -> List[str]:
        """生成趋势洞察"""
        insights = []
        
        # 分析最受欢迎的类型
        if "类型标签" in trends:
            top_type = trends["类型标签"].get("most_popular")
            if top_type:
                insights.append(f"最受欢迎的类型是'{top_type}'")
        
        # 分析多样性
        for category, data in trends.items():
            diversity = data.get("diversity_score", 0)
            if diversity > 0.5:
                insights.append(f"{category}具有较高的多样性")
            elif diversity < 0.2:
                insights.append(f"{category}相对集中在少数几个热门标签")
        
        return insights
    
    def _predict_trending_tags(self, tag_stats: Dict[str, Dict[str, int]]) -> Dict[str, List[str]]:
        """预测热门标签"""
        predictions = {}
        
        for category, stats in tag_stats.items():
            if stats:
                # 基于使用频率预测
                sorted_tags = sorted(stats.items(), key=lambda x: x[1], reverse=True)
                
                # 预测规则：取前30%的标签作为持续热门，中间部分作为上升趋势
                total_tags = len(sorted_tags)
                hot_count = max(1, total_tags // 3)
                
                predictions[category] = [tag for tag, _ in sorted_tags[:hot_count]]
        
        return predictions
