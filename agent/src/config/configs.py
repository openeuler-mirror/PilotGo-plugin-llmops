import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            current_file = Path(__file__)
            parent_dir = current_file.parent.parent.parent
            config_path = parent_dir / 'config.yaml'

        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        content = self.config_path.read_text(encoding='utf-8')

        if self.config_path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(content)
        elif self.config_path.suffix == '.json':
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported config file format: {self.config_path}")

    @property
    def llm_config(self) -> Dict[str, Any]:
        return self.config.get('llm', {})
# 创建全局配置实例
config = Config()
def get_llm_config():
    """获取 LLM 配置"""
    return config.llm_config
