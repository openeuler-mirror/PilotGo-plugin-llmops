from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from mcp_tools.cmd_safety_guard import validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(msg)s',
)
logger = logging.getLogger('nginx_set_config_check')

def verify_nginx_config_syntax(config_path: Optional[str] = None, config_content: Optional[str] = None) -> Dict:
    """
    校验 Nginx 配置文件语法正确性，返回错误信息、错误行号及修复建议

    参数:
        config_path: 配置文件路径，如果提供则检查该文件
        config_content: 配置内容字符串，如果提供则检查该内容

    返回:
        Dict: 包含语法检查结果的字典
    """
    try:
        # 安全验证：验证 config_path 参数（允许绝对路径）
        if config_path is not None:
            valid, error_msg = validate_path_param(config_path, allow_absolute=True)
            if not valid:
                logger.error(f"verify_nginx_config_syntax: config_path 路径验证失败：{error_msg}")
                return {
                    'success': False,
                    'msg': f'配置文件路径不安全：{error_msg}',
                    'errors': [],
                    'warnings': []
                }

        # 验证参数
        if not config_path and not config_content:
            return {
                'success': False,
                'msg': '必须提供配置文件路径或配置内容',
                'errors': [],
                'warnings': []
            }

        # 检查Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'msg': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'errors': [],
                'warnings': []
            }

        # 准备配置文件
        if config_path:
            if not os.path.exists(config_path):
                return {
                    'success': False,
                    'msg': f'配置文件不存在: {config_path}',
                    'errors': [],
                    'warnings': []
                }

            # 检查文件权限
            if not os.access(config_path, os.R_OK):
                return {
                    'success': False,
                    'msg': f'没有读取权限: {config_path}',
                    'errors': [],
                    'warnings': []
                }

            # 使用实际文件路径
            temp_config_path = config_path
            config_type = 'file'

        else:
            # 创建临时文件来检查配置内容
            temp_config_path = build_temp_config_file(config_content)
            config_type = 'body'

        # 执行语法检查
        syntax_result = invoke_syntax_check(temp_config_path)

        # 解析错误信息
        parsed_errors = analyze_error_messages(syntax_result, temp_config_path, config_content)

        # 生成修复建议
        suggestions = produce_fix_suggestions(parsed_errors)

        # 清理临时文件
        if config_type == 'body':
            os.unlink(temp_config_path)

        # 返回结果
        return {
            'success': syntax_result['valid'],
            'msg': '语法检查完成',
            'config_type': config_type,
            'config_path': config_path if config_path else '临时文件',
            'valid': syntax_result['valid'],
            'errors': parsed_errors['errors'],
            'warnings': parsed_errors['warnings'],
            'suggestions': suggestions,
            'check_time': syntax_result['check_time'],
            'nginx_version': syntax_result['nginx_version']
        }

    except Exception as e:
        logger.error(f'语法检查失败: {e}')
        return {
            'success': False,
            'msg': f'语法检查失败: {e}',
            'errors': [],
            'warnings': []
        }

def verify_nginx_installation() -> Dict:
    """检查Nginx安装状态"""
    try:
        output = subprocess.run(['which', 'nginx'], capture_output=True, text=True)
        if output.returncode != 0:
            return {
                'installed': False,
                'suggestion': '请使用包管理器安装Nginx (如: apt install nginx 或 yum install nginx)'
            }

        ngx_bin_path = output.stdout.strip()
        if not os.path.exists(ngx_bin_path):
            return {
                'installed': False,
                'suggestion': 'Nginx二进制文件不存在，请重新安装'
            }

        return {'installed': True, 'path': ngx_bin_path}

    except Exception as e:
        logger.error(f'检查Nginx安装状态失败: {e}')
        return {
            'installed': False,
            'suggestion': f'检查安装状态时出错: {e}'
        }

def build_temp_config_file(config_content: str) -> str:
    """创建临时配置文件"""
    try:
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
        temp_file.write(config_content)
        temp_file.close()

        return temp_file.name

    except Exception as e:
        logger.error(f'创建临时配置文件失败: {e}')
        raise

def invoke_syntax_check(config_path: str) -> Dict:
    """执行 Nginx 语法检查"""
    try:
        # 安全验证：验证 config_path 参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_path, allow_absolute=True)
        if not valid:
            logger.error(f"invoke_syntax_check: config_path 路径验证失败：{error_msg}")
            return {
                'valid': False,
                'returncode': -1,
                'stdout': '',
                'stderr': f'配置文件路径不安全：{error_msg}',
                'check_time': 0.0,
                'nginx_version': 'Unknown'
            }

        start_time = subprocess.getoutput('date +%s.%N')

        # 执行nginx -t命令
        output = subprocess.run(
            ['nginx', '-t', '-c', config_path],
            capture_output=True,
            text=True,
            timeout=30  # 30秒超时
        )

        end_time = subprocess.getoutput('date +%s.%N')
        check_time = float(end_time) - float(start_time)

        # 获取Nginx版本
        version_result = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        nginx_version = 'Unknown'
        if version_result.returncode == 0:
            ver_match = re.search(r'nginx/([\d\.]+)', version_result.stderr or version_result.stdout)  # NOSONAR
            if ver_match:
                nginx_version = ver_match.group(1)

        return {
            'valid': output.returncode == 0,
            'returncode': output.returncode,
            'stdout': output.stdout,
            'stderr': output.stderr,
            'check_time': check_time,
            'nginx_version': nginx_version
        }

    except subprocess.TimeoutExpired:
        logger.error('语法检查超时')
        return {
            'valid': False,
            'returncode': -1,
            'stdout': '',
            'stderr': '语法检查超时（超过30秒）',
            'check_time': 30.0,
            'nginx_version': 'Unknown'
        }
    except Exception as e:
        logger.error(f'执行语法检查失败: {e}')
        return {
            'valid': False,
            'returncode': -1,
            'stdout': '',
            'stderr': f'执行语法检查失败: {e}',
            'check_time': 0.0,
            'nginx_version': 'Unknown'
        }

def analyze_error_messages(syntax_result: Dict, config_path: str, config_content: Optional[str] = None) -> Dict:
    """解析错误信息"""
    errors = []
    warnings = []

    try:
        # 如果没有错误，直接返回
        if syntax_result['valid']:
            return {'errors': errors, 'warnings': warnings}

        # 获取错误输出
        error_output = syntax_result['stderr'] or syntax_result['stdout']
        if not error_output:
            errors.append({
                'line_number': 0,
                'msg': '未知语法错误',
                'error_type': 'unknown',
                'context': ''
            })
            return {'errors': errors, 'warnings': warnings}

        # 解析错误行
        error_lines = error_output.split('\n')

        for line in error_lines:
            if not line.strip():
                continue

            # 解析常见的错误模式
            error_info = analyze_error_line(line, config_path, config_content)
            if error_info:
                if error_info.get('severity', 'error') == 'warning':
                    warnings.append(error_info)
                else:
                    errors.append(error_info)

        return {'errors': errors, 'warnings': warnings}

    except Exception as e:
        logger.error(f'解析错误信息失败: {e}')
        errors.append({
            'line_number': 0,
            'msg': f'解析错误信息失败: {e}',
            'error_type': 'parse_error',
            'context': ''
        })
        return {'errors': errors, 'warnings': warnings}

def analyze_error_line(error_line: str, config_path: str, config_content: Optional[str] = None) -> Optional[Dict]:
    """解析单行错误信息"""
    try:
        # 常见的Nginx错误模式
        patterns = [
            # 模式1: nginx: [emerg] invalid parameter "xxx" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*(.+?)\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式2: nginx: [emerg] unknown directive "xxx" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*unknown directive\s+"([^"]+)"\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式3: nginx: [emerg] directive "xxx" is not terminated by ";" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*directive\s+"([^"]+)"\s+is not terminated by\s+"([^"]+)"\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式4: nginx: [emerg] invalid number of arguments in "xxx" directive in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*invalid number of arguments in\s+"([^"]+)"\s+directive\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式5: nginx: [emerg] host not found in "xxx" of the "listen" directive in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*host not found in\s+"([^"]+)"\s+of the\s+"([^"]+)"\s+directive\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式6: nginx: [emerg] duplicate location "/xxx" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*duplicate\s+([^"]+)\s+"([^"]+)"\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式7: nginx: [warn] ...
            r'nginx:\s*\[warn\]\s*(.+)',

            # 模式8: 通用错误模式
            r'nginx:\s*\[emerg\]\s*(.+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, error_line, re.IGNORECASE)  # NOSONAR
            if match:
                groups = match.groups()

                # 根据模式类型处理
                if pattern == patterns[0]:  # 模式1
                    return {
                        'line_number': int(groups[2]),
                        'msg': groups[0],
                        'error_type': 'invalid_parameter',
                        'directive': derive_directive_from_context(groups[0]),
                        'file_path': groups[1],
                        'severity': 'error'
                    }

                elif pattern == patterns[1]:  # 模式2
                    return {
                        'line_number': int(groups[2]),
                        'msg': f'未知指令: {groups[0]}',
                        'error_type': 'unknown_directive',
                        'directive': groups[0],
                        'file_path': groups[1],
                        'severity': 'error'
                    }

                elif pattern == patterns[2]:  # 模式3
                    return {
                        'line_number': int(groups[3]),
                        'msg': f'指令 "{groups[0]}" 未以 "{groups[1]}" 结尾',
                        'error_type': 'unterminated_directive',
                        'directive': groups[0],
                        'file_path': groups[2],
                        'severity': 'error'
                    }

                elif pattern == patterns[3]:  # 模式4
                    return {
                        'line_number': int(groups[2]),
                        'msg': f'指令 "{groups[0]}" 参数数量无效',
                        'error_type': 'invalid_arguments',
                        'directive': groups[0],
                        'file_path': groups[1],
                        'severity': 'error'
                    }

                elif pattern == patterns[4]:  # 模式5
                    return {
                        'line_number': int(groups[3]),
                        'msg': f'在 "{groups[1]}" 指令中找不到主机 "{groups[0]}"',
                        'error_type': 'host_not_found',
                        'directive': groups[1],
                        'file_path': groups[2],
                        'severity': 'error'
                    }

                elif pattern == patterns[5]:  # 模式6
                    return {
                        'line_number': int(groups[3]),
                        'msg': f'重复的 {groups[0]}: {groups[1]}',
                        'error_type': 'duplicate_config',
                        'config_type': groups[0],
                        'file_path': groups[2],
                        'severity': 'error'
                    }

                elif pattern == patterns[6]:  # 模式7
                    return {
                        'line_number': 0,
                        'msg': groups[0],
                        'error_type': 'warning',
                        'severity': 'warning'
                    }

                elif pattern == patterns[7]:  # 模式8
                    return {
                        'line_number': 0,
                        'msg': groups[0],
                        'error_type': 'general_error',
                        'severity': 'error'
                    }

        # 如果未匹配任何模式，返回通用错误
        return {
            'line_number': 0,
            'msg': error_line.strip(),
            'error_type': 'unknown_error',
            'severity': 'error'
        }

    except Exception as e:
        logger.error(f'解析错误行失败: {e}')
        return None

def derive_directive_from_context(context: str) -> str:
    """从错误上下文中提取指令名称"""
    try:
        # 常见的指令模式
        directive_patterns = [
            r'in\s+"([^"]+)"\s+directive',
            r'directive\s+"([^"]+)"',
            r'parameter\s+"([^"]+)"',
        ]

        for pattern in directive_patterns:
            match = re.search(pattern, context, re.IGNORECASE)  # NOSONAR
            if match:
                return match.group(1)

        return 'unknown'

    except Exception:
        return 'unknown'

def produce_fix_suggestions(parsed_errors: Dict) -> List[Dict]:
    """生成修复建议"""
    suggestions = []

    try:
        # 处理错误
        for error in parsed_errors['errors']:
            suggestion = produce_single_suggestion(error)
            if suggestion:
                suggestions.append(suggestion)

        # 处理警告
        for warning in parsed_errors['warnings']:
            suggestion = produce_single_suggestion(warning, is_warning=True)
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    except Exception as e:
        logger.error(f'生成修复建议失败: {e}')
        return []

def produce_single_suggestion(error_info: Dict, is_warning: bool = False) -> Optional[Dict]:
    """为单个错误/警告生成修复建议"""
    try:
        error_type = error_info.get('error_type', '')
        msg = error_info.get('msg', '')
        line_number = error_info.get('line_number', 0)
        directive = error_info.get('directive', '')

        suggestion_template = {
            'line_number': line_number,
            'error_type': error_type,
            'msg': msg,
            'suggestion': '',
            'severity': 'warning' if is_warning else 'error'
        }

        # 根据错误类型生成具体建议
        if error_type == 'unknown_directive':
            suggestion_template['suggestion'] = f'检查指令 "{directive}" 的拼写是否正确，或确认该指令在当前Nginx版本中是否可用'

        elif error_type == 'unterminated_directive':
            suggestion_template['suggestion'] = f'在指令 "{directive}" 的末尾添加分号 (;)'

        elif error_type == 'invalid_arguments':
            suggestion_template['suggestion'] = f'检查指令 "{directive}" 的参数数量和格式是否正确'

        elif error_type == 'invalid_parameter':
            suggestion_template['suggestion'] = f'检查指令 "{directive}" 的参数值是否有效'

        elif error_type == 'host_not_found':
            suggestion_template['suggestion'] = f'确认主机名 "{directive}" 可以正确解析，或使用IP地址替代'

        elif error_type == 'duplicate_config':
            suggestion_template['suggestion'] = f'移除重复的配置项，或合并相同的配置'

        elif 'syntax error' in msg.lower():
            suggestion_template['suggestion'] = '检查配置语法，确保指令格式正确，参数使用恰当'

        elif 'permission denied' in msg.lower():
            suggestion_template['suggestion'] = '检查文件权限，确保Nginx进程有读取配置文件的权限'

        elif 'no such file' in msg.lower():
            suggestion_template['suggestion'] = '检查文件路径是否正确，文件是否存在'

        else:
            # 通用建议
            suggestion_template['suggestion'] = '检查配置语法，参考Nginx官方文档确认指令用法'

        return suggestion_template

    except Exception as e:
        logger.error(f'生成单个修复建议失败: {e}')
        return None

def certify_config_structure(config_path: str) -> Dict:
    """
    验证配置文件结构完整性

    参数:
        config_path: 配置文件路径

    返回:
        Dict: 结构验证结果
    """
    try:
        # 安全验证：验证 config_path 参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_path, allow_absolute=True)
        if not valid:
            logger.error(f"certify_config_structure: config_path 路径验证失败：{error_msg}")
            return {
                'valid': False,
                'issues': [{'type': 'security_error', 'msg': f'配置文件路径不安全：{error_msg}'}]
            }

        body = Path(config_path).read_text(encoding='utf-8')

        issues = []

        # 检查基本结构
        if 'events' not in body:
            issues.append({
                'type': 'missing_section',
                'section': 'events',
                'severity': 'warning',
                'msg': '缺少events块，建议添加基本的events配置'
            })

        if 'http' not in body:
            issues.append({
                'type': 'missing_section',
                'section': 'http',
                'severity': 'error',
                'msg': '缺少http块，这是必需的配置块'
            })

        # 检查常见的配置问题
        lines = body.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()

            # 检查未闭合的花括号
            if '{' in line and '}' not in line:
                # 检查后续行是否有匹配的}
                brace_count = 1
                for j in range(i, min(i + 10, len(lines))):  # 检查后续10行
                    if '{' in lines[j]:
                        brace_count += 1
                    if '}' in lines[j]:
                        brace_count -= 1
                    if brace_count == 0:
                        break

                if brace_count > 0:
                    issues.append({
                        'type': 'unclosed_brace',
                        'line': i,
                        'severity': 'error',
                        'msg': f'第{i}行可能有未闭合的花括号'
                    })

            # 检查指令后缺少分号
            if line and not line.startswith('#') and not line.endswith(';') and not line.endswith('{') and not line.endswith('}'):
                # 排除空行和注释
                if not re.match(r'^\s*(#|$)', line):  # NOSONAR
                    issues.append({
                        'type': 'missing_semicolon',
                        'line': i,
                        'severity': 'warning',
                        'msg': f'第{i}行可能缺少分号'
                    })

        return {
            'success': len([i for i in issues if i['severity'] == 'error']) == 0,
            'issues': issues,
            'total_issues': len(issues),
            'error_count': len([i for i in issues if i['severity'] == 'error']),
            'warning_count': len([i for i in issues if i['severity'] == 'warning'])
        }

    except Exception as e:
        logger.error(f'验证配置结构失败: {e}')
        return {
            'success': False,
            'issues': [{
                'type': 'validation_error',
                'severity': 'error',
                'msg': f'验证配置结构失败: {e}'
            }],
            'total_issues': 1,
            'error_count': 1,
            'warning_count': 0
        }

# MCP工具配置
TOOL_CONFIG = {
    "name": "verify_nginx_config_syntax",
    "function": verify_nginx_config_syntax,
    "description": "校验Nginx配置文件语法正确性，返回错误信息、错误行号及修复建议",
    "version": "1.0.0",
    "author": "Nginx配置工具",
    "parameters": {
        "type": "object",
        "properties": {
            "config_path": {
                "type": "string",
                "description": "配置文件路径"
            },
            "config_content": {
                "type": "string",
                "description": "配置内容字符串"
            }
        },
        "oneOf": [
            {"required": ["config_path"]},
            {"required": ["config_content"]}
        ]
    },
    "examples": [
        {
            "name": "verify_nginx_config_syntax",
            "arguments": {
                "config_path": "/etc/nginx/nginx.conf"
            }
        },
        {
            "name": "verify_nginx_config_syntax",
            "arguments": {
                "config_content": "server { listen 80; server_name example.com; }"
            }
        }
    ]
}
