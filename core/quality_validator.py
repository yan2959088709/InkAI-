"""
事前质量验证模块
在章节生成前验证内容是否符合质量标准
"""

from typing import Dict, List, Any, Optional
import config


class QualityValidator:
    """章节质量验证器"""

    # 字数要求范围
    WORD_COUNT_MIN = 3000
    WORD_COUNT_MAX = 5000

    # 模板循环相似度阈值
    TEMPLATE_LOOP_THRESHOLD = 0.8

    # 结尾比较时使用的字符数量
    ENDING_COMPARISON_LENGTH = 200

    def __init__(self):
        """初始化质量验证器"""
        self.log("质量验证器初始化完成")

    def log(self, message: str):
        """日志记录"""
        print(f"[QualityValidator] {message}")

    def validate_chapter(self, chapter_content: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证单章质量

        Args:
            chapter_content: 章节正文内容
            requirements: 验证要求，包含protagonist_name等

        Returns:
            验证结果字典
        """
        errors = []
        validations = {}

        # 1. 验证字数
        word_count_result = self.validate_word_count(chapter_content)
        validations["word_count"] = word_count_result
        if not word_count_result["passed"]:
            errors.append(f"字数验证失败：实际字数{word_count_result['actual']}字，"
                         f"要求{word_count_result['required']}字")

        # 2. 验证主角出场
        protagonist_name = requirements.get("protagonist_name", "")
        if protagonist_name:
            protagonist_result = self.validate_protagonist_presence(chapter_content, protagonist_name)
            validations["protagonist"] = protagonist_result
            if not protagonist_result["passed"]:
                errors.append(f"主角'{protagonist_name}'验证失败：出场次数{protagonist_result['count']}次")

        # 3. 验证模板循环
        previous_chapters = requirements.get("previous_chapters", [])
        if previous_chapters:
            loop_result = self.detect_template_loop(chapter_content, previous_chapters)
            validations["template_loop"] = {
                "passed": loop_result["is_loop"] is False,
                "similarity": loop_result["similarity"]
            }
            if loop_result["is_loop"]:
                errors.append(f"模板循环检测：{loop_result['message']}")

        # 判断是否通过所有验证
        passed = len(errors) == 0

        self.log(f"章节质量验证完成：通过={passed}，错误数={len(errors)}")

        return {
            "passed": passed,
            "validations": validations,
            "errors": errors
        }

    def validate_word_count(self, content: str) -> Dict[str, Any]:
        """
        验证字数是否在3000-5000字之间

        Args:
            content: 章节正文内容

        Returns:
            字数验证结果
        """
        if not content:
            actual = 0
        else:
            clean_content = content.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\u3000', '')
            actual = len(clean_content)

        passed = self.WORD_COUNT_MIN <= actual <= self.WORD_COUNT_MAX

        self.log(f"字数验证：实际={actual}字，范围={self.WORD_COUNT_MIN}-{self.WORD_COUNT_MAX}字，通过={passed}")

        return {
            "passed": passed,
            "actual": actual,
            "required": f"{self.WORD_COUNT_MIN}-{self.WORD_COUNT_MAX}"
        }

    def validate_protagonist_presence(self, content: str, protagonist_name: str) -> Dict[str, Any]:
        """
        验证主角是否出场（>0次）

        Args:
            content: 章节正文内容
            protagonist_name: 主角名称

        Returns:
            主角出场验证结果
        """
        if not content or not protagonist_name:
            count = 0
        else:
            count = content.count(protagonist_name)

        passed = count > 0

        self.log(f"主角出场验证：'{protagonist_name}'出场{count}次，通过={passed}")

        return {
            "passed": passed,
            "count": count
        }

    def detect_template_loop(self, content: str, previous_chapters: List[str]) -> Dict[str, Any]:
        """
        检测模板循环，识别固定结尾模式

        检测逻辑：
        1. 提取本章结尾部分
        2. 与前几章结尾进行比较
        3. 如果相似度超过阈值，认为是模板循环

        Args:
            content: 本章正文内容
            previous_chapters: 前几章正文内容列表

        Returns:
            模板循环检测结果，包含is_loop, similarity, message
        """
        if not content or not previous_chapters:
            return {
                "is_loop": False,
                "similarity": 0.0,
                "message": "无可比较的历史章节或本章内容为空"
            }

        current_ending = self._extract_ending(content)

        max_similarity = 0.0
        most_similar_chapter = 0

        for i, prev_content in enumerate(previous_chapters):
            if not prev_content:
                continue

            prev_ending = self._extract_ending(prev_content)
            similarity = self._calculate_similarity(current_ending, prev_ending)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_chapter = i + 1

        is_loop = max_similarity >= self.TEMPLATE_LOOP_THRESHOLD

        if is_loop:
            message = f"检测到模板循环：与第{most_similar_chapter}章结尾相似度为{max_similarity:.2%}，超过阈值{self.TEMPLATE_LOOP_THRESHOLD:.2%}"
        else:
            message = f"未检测到模板循环：最高相似度为{max_similarity:.2%}（与第{most_similar_chapter}章），低于阈值{self.TEMPLATE_LOOP_THRESHOLD:.2%}"

        self.log(message)

        return {
            "is_loop": is_loop,
            "similarity": round(max_similarity, 4),
            "message": message
        }

    def _extract_ending(self, content: str) -> str:
        """
        提取章节结尾部分

        Args:
            content: 章节正文内容

        Returns:
            章节结尾部分
        """
        if not content:
            return ""

        length = len(content)
        extract_length = min(self.ENDING_COMPARISON_LENGTH, length)

        return content[-extract_length:]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（基于字符重叠率）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度分数（0-1之间）
        """
        if not text1 or not text2:
            return 0.0

        set1 = set(text1)
        set2 = set(text2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        jaccard_similarity = intersection / union

        return jaccard_similarity
