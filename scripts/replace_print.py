"""
批量替换 print 为 logging 的脚本
"""

import os
import re
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def replace_print_in_file(filepath: str) -> int:
    """替换文件中的 print 语句"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 检查是否已经有 logger 导入
        has_logger_import = 'from utils.logger import' in content or 'import logging' in content
        
        # 获取模块名（用于logger）
        module_name = os.path.basename(filepath).replace('.py', '')
        
        # 替换 print 语句
        # 匹配模式: print(f"xxx") 或 print("xxx") 或 print(xxx)
        lines = content.split('\n')
        new_lines = []
        
        added_import = False
        replacements = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 跳过注释和空行
            if stripped.startswith('#') or not stripped:
                new_lines.append(line)
                continue
            
            # 检查是否是 print 语句
            if re.match(r'^(\s*)print\s*\(', line):
                # 提取缩进
                indent = match.group(1) if (match := re.match(r'^(\s*)', line)) else ''
                
                # 替换 print 为 logger.info/error/warning
                # 根据内容判断日志级别
                if '错误' in line or '失败' in line or 'error' in line.lower() or 'fail' in line.lower():
                    log_func = 'logger.error'
                elif '警告' in line or 'warn' in line.lower():
                    log_func = 'logger.warning'
                elif '调试' in line or 'debug' in line.lower():
                    log_func = 'logger.debug'
                else:
                    log_func = 'logger.info'
                
                # 替换 print( 为 logger.xxx(
                new_line = re.sub(r'print\s*\(', f'{log_func}(', line)
                new_lines.append(new_line)
                replacements += 1
                
                # 添加导入（如果还没有）
                if not has_logger_import and not added_import:
                    # 在文件开头添加导入
                    added_import = True
            else:
                new_lines.append(line)
        
        if replacements > 0:
            # 组装新内容
            new_content = '\n'.join(new_lines)
            
            # 添加 logger 导入和初始化
            if added_import:
                import_line = f'from utils.logger import get_logger\nlogger = get_logger("{module_name}")\n'
                
                # 找到合适的位置插入导入（在其他导入之后）
                import_section_end = 0
                for i, line in enumerate(new_content.split('\n')):
                    if line.startswith('import ') or line.startswith('from '):
                        import_section_end = i + 1
                
                lines_list = new_content.split('\n')
                lines_list.insert(import_section_end, import_line)
                new_content = '\n'.join(lines_list)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return replacements
        
        return 0
        
    except Exception as e:
        print(f"处理文件 {filepath} 失败: {e}")
        return 0


def main():
    """主函数"""
    print("=" * 50)
    print("批量替换 print 为 logging")
    print("=" * 50)
    
    # 需要处理的目录
    directories = ['.', 'agents', 'core', 'utils', 'performance', 'optimization']
    
    total_replacements = 0
    files_modified = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
        
        for filename in os.listdir(directory):
            if filename.endswith('.py') and filename != '__init__.py':
                filepath = os.path.join(directory, filename)
                replacements = replace_print_in_file(filepath)
                
                if replacements > 0:
                    print(f"  [OK] {filepath}: {replacements} 个替换")
                    total_replacements += replacements
                    files_modified += 1
    
    print(f"\n总计: {files_modified} 个文件修改, {total_replacements} 个替换")


if __name__ == "__main__":
    main()
