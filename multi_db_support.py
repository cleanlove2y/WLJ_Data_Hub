#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
多数据库环境支持模块
为generate_data_dictionary.py脚本提供多数据库环境支持
"""

import os
import configparser
import argparse

def read_multi_env_config(config_file, env=None):
    """
    读取多环境配置文件
    
    Args:
        config_file: 配置文件路径
        env: 环境名称，如果为None则使用默认环境
        
    Returns:
        配置字典
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    # 检查是否是多环境配置文件
    if 'environment' in config and 'default' in config['environment']:
        is_multi_env = True
        default_env = config['environment']['default']
    else:
        is_multi_env = False
    
    # 如果是多环境配置但未指定环境，则使用默认环境
    if is_multi_env and env is None:
        env = default_env
        print(f"未指定环境，使用默认环境: {env}")
    
    # 构建配置字典
    result = {}
    
    if is_multi_env:
        # 多环境配置
        db_section = f"database:{env}"
        if db_section not in config:
            raise ValueError(f"环境 '{env}' 在配置文件中不存在")
        
        result['database'] = dict(config[db_section])
        
        # 添加其他非数据库配置
        for section in config.sections():
            if section != 'environment' and not section.startswith('database:'):
                result[section] = dict(config[section])
    else:
        # 单环境配置
        for section in config.sections():
            result[section] = dict(config[section])
    
    return result

def list_environments(config_file):
    """
    列出配置文件中的所有环境
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        环境列表
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    environments = []
    default_env = None
    
    # 检查是否是多环境配置文件
    if 'environment' in config and 'default' in config['environment']:
        default_env = config['environment']['default']
        
        # 查找所有数据库环境
        for section in config.sections():
            if section.startswith('database:'):
                env_name = section.split(':')[1]
                environments.append(env_name)
    
    return environments, default_env

def main():
    """测试函数"""
    parser = argparse.ArgumentParser(description='多数据库环境配置测试')
    parser.add_argument('--config', type=str, default='config_multi_env.ini', help='配置文件路径')
    parser.add_argument('--env', type=str, help='环境名称')
    parser.add_argument('--list', action='store_true', help='列出所有环境')
    args = parser.parse_args()
    
    if args.list:
        environments, default_env = list_environments(args.config)
        if environments:
            print(f"配置文件 '{args.config}' 中的环境:")
            for env in environments:
                if env == default_env:
                    print(f"  - {env} (默认)")
                else:
                    print(f"  - {env}")
        else:
            print(f"配置文件 '{args.config}' 不是多环境配置文件")
    else:
        try:
            config = read_multi_env_config(args.config, args.env)
            print("配置信息:")
            for section, items in config.items():
                print(f"[{section}]")
                for key, value in items.items():
                    print(f"  {key} = {value}")
        except Exception as e:
            print(f"错误: {e}")

if __name__ == '__main__':
    main()
