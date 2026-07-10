import logging
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('net_snat_dnat')

def fetch_net_snat_dnat():
    """
    采集SNAT/DNAT规则（地址转换规则/源/目标IP/端口/协议/生效链）

    返回:
        格式化的SNAT/DNAT规则信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== SNAT/DNAT规则 ===')

        # 采集SNAT规则
        snat_rules = fetch_snat_rules()
        if snat_rules:
            output.append('\nSNAT规则:')
            for i, rule in enumerate(snat_rules[:20], 1):
                display_rule_info(output, i, rule)
            if len(snat_rules) > 20:
                output.append(f"  ... 还有 {len(snat_rules) - 20} 条SNAT规则")
        else:
            output.append('\nSNAT规则: 无')

        # 采集DNAT规则
        dnat_rules = fetch_dnat_rules()
        if dnat_rules:
            output.append('\nDNAT规则:')
            for i, rule in enumerate(dnat_rules[:20], 1):
                display_rule_info(output, i, rule)
            if len(dnat_rules) > 20:
                output.append(f"  ... 还有 {len(dnat_rules) - 20} 条DNAT规则")
        else:
            output.append('\nDNAT规则: 无')

        # 采集规则统计
        rule_stats = fetch_rule_stats(snat_rules, dnat_rules)
        if rule_stats:
            output.append('\n规则统计:')
            for key, value in rule_stats.items():
                output.append(f"  {key}: {value}")

        # 检查规则状态
        rule_checks = verify_rule_status(snat_rules, dnat_rules)
        if rule_checks:
            output.append('\n规则状态检查:')
            for check in rule_checks:
                output.append(f"  - {check}")

        # 分析规则配置
        rule_analysis = examine_rule_config(snat_rules, dnat_rules)
        if rule_analysis:
            output.append('\n规则配置分析:')
            for analysis in rule_analysis:
                output.append(f"  - {analysis}")

        # 检查规则安全性
        rule_security = verify_rule_security(snat_rules, dnat_rules)
        if rule_security:
            output.append('\n规则安全性检查:')
            for check in rule_security:
                output.append(f"  - {check}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取SNAT/DNAT规则失败: {e}')
        return f'获取SNAT/DNAT规则失败: {e}'
def fetch_snat_rules():
    """
    获取SNAT规则
    """
    rules = []

    try:
        # 使用iptables命令获取SNAT规则
        output = subprocess.run(['iptables', '-t', 'nat', '-L', '-n', '--line-numbers'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            chain = ''
            for line in lines:
                if line.startswith('Chain'):
                    chain = line.strip()
                elif line and not line.startswith('target') and not line.startswith('---'):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        target = parts[1]
                        if target == 'SNAT' or target == 'MASQUERADE':
                            rule = {
                                '链': chain,
                                '目标': target,
                                '协议': parts[2],
                                '源IP': parts[3],
                                '目标IP': parts[4]
                            }
                            # 提取SNAT参数
                            if len(parts) > 4:
                                for i, part in enumerate(parts[5:]):
                                    if part == '-j':
                                        rule['动作'] = parts[i + 6] if i + 6 < len(parts) else ''
                                    elif part == '--to-source':
                                        rule['转换地址'] = parts[i + 6] if i + 6 < len(parts) else ''
                                    elif part == 'sport':
                                        rule['源端口'] = parts[i + 6] if i + 6 < len(parts) else ''
                                    elif part == 'dport':
                                        rule['目标端口'] = parts[i + 6] if i + 6 < len(parts) else ''
                            rules.append(rule)

    except Exception as e:
        logger.error(f'获取SNAT规则失败: {e}')

    return rules
def fetch_dnat_rules():
    """
    获取DNAT规则
    """
    rules = []

    try:
        # 使用iptables命令获取DNAT规则
        output = subprocess.run(['iptables', '-t', 'nat', '-L', '-n', '--line-numbers'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            chain = ''
            for line in lines:
                if line.startswith('Chain'):
                    chain = line.strip()
                elif line and not line.startswith('target') and not line.startswith('---'):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        target = parts[1]
                        if target == 'DNAT' or target == 'REDIRECT':
                            rule = {
                                '链': chain,
                                '目标': target,
                                '协议': parts[2],
                                '源IP': parts[3],
                                '目标IP': parts[4]
                            }
                            # 提取DNAT参数
                            if len(parts) > 4:
                                for i, part in enumerate(parts[5:]):
                                    if part == '-j':
                                        rule['动作'] = parts[i + 6] if i + 6 < len(parts) else ''
                                    elif part == '--to-destination':
                                        rule['转换地址'] = parts[i + 6] if i + 6 < len(parts) else ''
                                    elif part == 'sport':
                                        rule['源端口'] = parts[i + 6] if i + 6 < len(parts) else ''
                                    elif part == 'dport':
                                        rule['目标端口'] = parts[i + 6] if i + 6 < len(parts) else ''
                            rules.append(rule)

    except Exception as e:
        logger.error(f'获取DNAT规则失败: {e}')

    return rules
def display_rule_info(output, index, rule):
    """
    显示规则信息
    """
    output.append(f"  {index}.")
    output.append(f"    链: {rule.get('链', '未知')}")
    output.append(f"    目标: {rule.get('目标', '未知')}")
    output.append(f"    协议: {rule.get('协议', '未知')}")
    output.append(f"    源IP: {rule.get('源IP', '未知')}")
    output.append(f"    目标IP: {rule.get('目标IP', '未知')}")
    if '转换地址' in rule:
        output.append(f"    转换地址: {rule['转换地址']}")
    if '源端口' in rule:
        output.append(f"    源端口: {rule['源端口']}")
    if '目标端口' in rule:
        output.append(f"    目标端口: {rule['目标端口']}")
    if '动作' in rule:
        output.append(f"    动作: {rule['动作']}")
def fetch_rule_stats(snat_rules, dnat_rules):
    """
    获取规则统计
    """
    stats = {}

    try:
        # 统计规则数量
        stats['总规则数'] = len(snat_rules) + len(dnat_rules)
        stats['SNAT规则数'] = len(snat_rules)
        stats['DNAT规则数'] = len(dnat_rules)

        # 统计不同链的规则数
        chains = {}
        for rule in snat_rules + dnat_rules:
            chain = rule.get('链', '未知')
            chains[chain] = chains.get(chain, 0) + 1
        if chains:
            stats['链统计'] = chains

        # 统计不同协议的规则数
        protocols = {}
        for rule in snat_rules + dnat_rules:
            protocol = rule.get('协议', '未知')
            protocols[protocol] = protocols.get(protocol, 0) + 1
        if protocols:
            stats['协议统计'] = protocols

    except Exception as e:
        logger.error(f'获取规则统计失败: {e}')

    return stats
def verify_rule_status(snat_rules, dnat_rules):
    """
    检查规则状态
    """
    checks = []

    try:
        # 检查规则数量
        total_rules = len(snat_rules) + len(dnat_rules)
        if total_rules > 100:
            checks.append(f"规则数量较多 ({total_rules} 条)")

        # 检查是否有开放的规则
        for rule in snat_rules + dnat_rules:
            if rule.get('源IP') == '0.0.0.0/0':
                checks.append(f"警告: 发现源IP为 0.0.0.0/0 的规则")
            if rule.get('目标IP') == '0.0.0.0/0':
                checks.append(f"警告: 发现目标IP为 0.0.0.0/0 的规则")

    except Exception as e:
        logger.error(f'检查规则状态失败: {e}')

    return checks
def examine_rule_config(snat_rules, dnat_rules):
    """
    分析规则配置
    """
    analysis = []

    try:
        # 分析SNAT规则
        if snat_rules:
            analysis.append(f"SNAT规则主要分布在以下链: {', '.join(set(rule.get('链', '') for rule in snat_rules))}")

        # 分析DNAT规则
        if dnat_rules:
            analysis.append(f"DNAT规则主要分布在以下链: {', '.join(set(rule.get('链', '') for rule in dnat_rules))}")

        # 分析协议分布
        protocols = set()
        for rule in snat_rules + dnat_rules:
            protocols.add(rule.get('协议', ''))
        if protocols:
            analysis.append(f"规则涉及的协议: {', '.join(protocols)}")

    except Exception as e:
        logger.error(f'分析规则配置失败: {e}')

    return analysis
