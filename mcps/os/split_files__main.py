#!/usr/bin/env python3

import os
import ast
import re
import json

        if 'logging.basicConfig' in line:
            in_basicConfig = True
        if in_basicConfig:
            result.append(line)


def main():
    os.makedirs(SPLIT_DIR, exist_ok=True)

    all_entries = []

    # 拆分所有 py 文件
    for root, dirs, files in os.walk(PART1_DIR):
        dirs[:] = [d for d in dirs if d not in ('syq', 'yzy', 'split', '__pycache__', '.git')]
        for f in files:
            if not f.endswith('.py'):
                continue
            filepath = os.path.join(root, f)
            entries = split_file(filepath)
            all_entries.extend(entries)

    # 添加 __init__.py
    all_entries.extend(generate_init_files())

    # 写入拆分文件
    for entry in all_entries:
        if entry['type'] == 'full_file':
            continue  # 原始文件已存在
        out_dir = os.path.dirname(entry['local_path'])
        os.makedirs(out_dir, exist_ok=True)
        with open(entry['local_path'], 'w', encoding='utf-8') as f:
            f.write(entry['content'])

    # 统计
    func_count = sum(1 for e in all_entries if e['type'] == 'function')
    full_count = sum(1 for e in all_entries if e['type'] == 'full_file')
    tc_count = sum(1 for e in all_entries if e['type'] == 'tool_config')
    init_count = sum(1 for e in all_entries if e['type'] == 'init')

    print(f"拆分完成!")
    print(f"  函数文件: {func_count}")
    print(f"  完整文件: {full_count}")
    print(f"  TOOL_CONFIG: {tc_count}")
    print(f"  __init__.py: {init_count}")
    print(f"  总PR数: {len(all_entries)}")

    # 保存 PR 计划
    plan_path = os.path.join(PART1_DIR, 'pr_plan.json')
    # 分配到两个账号
    # 策略：函数文件交替分配，完整文件和 TOOL_CONFIG 给账号1，init 给账号2
    acc1_entries = []
    acc2_entries = []

    for i, entry in enumerate(all_entries):
        if entry['type'] == 'function':
            if i % 2 == 0:
                acc1_entries.append(entry)
            else:
                acc2_entries.append(entry)
        elif entry['type'] == 'full_file':
            acc1_entries.append(entry)
        elif entry['type'] == 'tool_config':
            acc2_entries.append(entry)
        elif entry['type'] == 'init':
            acc1_entries.append(entry)

    plan = {
        'account1': {
            'owner': 'songyuqin0686',
            'count': len(acc1_entries),
            'entries': acc1_entries,
        },
        'account2': {
            'owner': 'yzydev',
            'count': len(acc2_entries),
            'entries': acc2_entries,
        },
        'total': len(all_entries),
    }

    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\nPR计划已保存到: {plan_path}")
    print(f"  账号1 (songyuqin0686): {len(acc1_entries)} 个PR")
    print(f"  账号2 (yzydev): {len(acc2_entries)} 个PR")
