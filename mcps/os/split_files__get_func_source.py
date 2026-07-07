#!/usr/bin/env python3

import os
import ast
import re
import json


def get_func_source(lines, func_node):
    """从行号获取函数源码"""
    start = func_node.lineno - 1
    end = func_node.end_lineno if hasattr(func_node, 'end_lineno') else func_node.lineno
    return '\n'.join(lines[start:end])
