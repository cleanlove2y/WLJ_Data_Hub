#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import configparser
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text, inspect

# 导入多环境配置支持模块
try:
    from multi_db_support import read_multi_env_config, list_environments
except ImportError:
    print("警告: 未找到多环境配置支持模块 multi_db_support.py")
    read_multi_env_config = None
    list_environments = None

def read_config(config_path='config.ini', env=None):
    """Reads database configuration from config.ini."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # 检查是否使用多环境配置
    if read_multi_env_config is not None:
        try:
            # 尝试读取多环境配置
            config_dict = read_multi_env_config(config_path, env)
            
            # 验证必要的配置项
            required_sections = ['database', 'output']
            for section in required_sections:
                if section not in config_dict:
                    raise ValueError(f"Missing section '{section}' in config file")
            
            required_db_options = ['type', 'host', 'port', 'database', 'user', 'password']
            for option in required_db_options:
                if option not in config_dict['database']:
                    raise ValueError(f"Missing option '{option}' in [database] section")
            
            return config_dict
        except Exception as e:
            print(f"警告: 多环境配置读取失败: {e}")
            print("尝试使用标准配置格式读取...")
    
    # 使用标准配置格式读取
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    
    # 验证必要的配置项
    required_sections = ['database', 'output']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing section '{section}' in config file")
    
    required_db_options = ['type', 'host', 'port', 'database', 'user', 'password']
    for option in required_db_options:
        if option not in config['database']:
            raise ValueError(f"Missing option '{option}' in [database] section")
    
    # 转换为字典格式，保持与多环境配置格式一致
    config_dict = {}
    for section in config.sections():
        config_dict[section] = dict(config[section])
    
    return config_dict

def get_db_connection_string(db_config):
    """Constructs the SQLAlchemy connection string based on database type."""
    db_type = db_config['type'].lower()
    host = db_config['host']
    port = db_config['port']
    database = db_config['database']
    user = quote_plus(db_config['user'])
    password = quote_plus(db_config['password'])

    if db_type == 'mysql':
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    elif db_type == 'postgresql':
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    elif db_type == 'sqlserver':
        # 从配置文件中获取驱动程序名称，如果未指定则使用默认值
        driver = db_config.get('driver', 'SQL Server')
        driver_param = quote_plus(driver)
        
        # 构建连接字符串
        conn_str = f"mssql+pyodbc://{user}:{password}@{host}"
        
        # 如果指定了端口，则添加端口
        if port:
            conn_str += f":{port}"
            
        # 添加数据库名和驱动程序
        conn_str += f"/{database}?driver={driver_param}"
        
        return conn_str
    elif db_type == 'oracle':
        # For Oracle, you might need cx_Oracle
        return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def get_table_comments_mysql(inspector, table_name):
    """Fetches table comments for MySQL."""
    # MySQL table comments are typically part of CREATE TABLE statement or INFORMATION_SCHEMA.TABLES
    # SQLAlchemy inspector doesn't directly expose table comments in a unified way
    # We'll try to get it from INFORMATION_SCHEMA
    try:
        with inspector.engine.connect() as connection:
            result = connection.execute(text(
                f"SELECT TABLE_COMMENT FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name"
            ), {"db_name": inspector.engine.url.database, "table_name": table_name})
            comment = result.scalar_one_or_none()
            return comment if comment else ''
    except Exception as e:
        print(f"Warning: Could not fetch table comment for {table_name} (MySQL): {e}")
        return ''

def get_column_comments_mysql(inspector, table_name):
    """Fetches column comments for MySQL."""
    comments = {}
    try:
        with inspector.engine.connect() as connection:
            result = connection.execute(text(
                f"SELECT COLUMN_NAME, COLUMN_COMMENT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name"
            ), {"db_name": inspector.engine.url.database, "table_name": table_name})
            for row in result:
                comments[row.COLUMN_NAME] = row.COLUMN_COMMENT
    except Exception as e:
        print(f"Warning: Could not fetch column comments for {table_name} (MySQL): {e}")
    return comments

def get_table_comments_postgresql(inspector, table_name):
    """Fetches table comments for PostgreSQL."""
    try:
        with inspector.engine.connect() as connection:
            result = connection.execute(text(
                f"SELECT obj_description(relfilenode, 'pg_class') FROM pg_class WHERE relname = :table_name"
            ), {"table_name": table_name})
            comment = result.scalar_one_or_none()
            return comment if comment else ''
    except Exception as e:
        print(f"Warning: Could not fetch table comment for {table_name} (PostgreSQL): {e}")
        return ''

def get_column_comments_postgresql(inspector, table_name):
    """Fetches column comments for PostgreSQL."""
    comments = {}
    try:
        with inspector.engine.connect() as connection:
            result = connection.execute(text(
                f"SELECT a.attname AS column_name, d.description AS column_comment FROM pg_class c JOIN pg_attribute a ON a.attrelid = c.oid LEFT JOIN pg_description d ON d.objoid = a.attrelid AND d.objsubid = a.attnum WHERE c.relname = :table_name AND a.attnum > 0"
            ), {"table_name": table_name})
            for row in result:
                comments[row.column_name] = row.column_comment if row.column_comment else ''
    except Exception as e:
        print(f"Warning: Could not fetch column comments for {table_name} (PostgreSQL): {e}")
    return comments

def get_table_comments_sqlserver(inspector, table_name):
    """Fetches table comments for SQL Server (extended properties)."""
    try:
        with inspector.engine.connect() as connection:
            # 避免使用 NVARCHAR(MAX) 和 CAST
            result = connection.execute(text(
                f"SELECT value FROM sys.extended_properties WHERE major_id = OBJECT_ID(:table_name) AND minor_id = 0 AND name = 'MS_Description'"
            ), {"table_name": table_name})
            comment = result.scalar_one_or_none()
            return str(comment) if comment else ''
    except Exception as e:
        print(f"Warning: Could not fetch table comment for {table_name} (SQL Server): {e}")
        return ''

def get_column_comments_sqlserver(inspector, table_name):
    """Fetches column comments for SQL Server (extended properties)."""
    comments = {}
    try:
        with inspector.engine.connect() as connection:
            # 避免使用 NVARCHAR(MAX) 和 CAST
            result = connection.execute(text(
                f"SELECT c.name AS column_name, ep.value AS column_comment FROM sys.columns c LEFT JOIN sys.extended_properties ep ON ep.major_id = c.object_id AND ep.minor_id = c.column_id AND ep.name = 'MS_Description' WHERE c.object_id = OBJECT_ID(:table_name)"
            ), {"table_name": table_name})
            for row in result:
                comments[row.column_name] = str(row.column_comment) if row.column_comment else ''
    except Exception as e:
        print(f"Warning: Could not fetch column comments for {table_name} (SQL Server): {e}")
    return comments

def get_table_comments_oracle(inspector, table_name):
    """Fetches table comments for Oracle."""
    try:
        with inspector.engine.connect() as connection:
            result = connection.execute(text(
                f"SELECT COMMENTS FROM ALL_TAB_COMMENTS WHERE TABLE_NAME = :table_name AND OWNER = :owner"
            ), {"table_name": table_name.upper(), "owner": inspector.engine.url.username.upper()})
            comment = result.scalar_one_or_none()
            return comment if comment else ''
    except Exception as e:
        print(f"Warning: Could not fetch table comment for {table_name} (Oracle): {e}")
        return ''

def get_column_comments_oracle(inspector, table_name):
    """Fetches column comments for Oracle."""
    comments = {}
    try:
        with inspector.engine.connect() as connection:
            result = connection.execute(text(
                f"SELECT COLUMN_NAME, COMMENTS FROM ALL_COL_COMMENTS WHERE TABLE_NAME = :table_name AND OWNER = :owner"
            ), {"table_name": table_name.upper(), "owner": inspector.engine.url.username.upper()})
            for row in result:
                comments[row.COLUMN_NAME] = row.COMMENTS if row.COMMENTS else ''
    except Exception as e:
        print(f"Warning: Could not fetch column comments for {table_name} (Oracle): {e}")
    return comments

def get_sqlserver_tables(engine):
    """自定义函数，获取SQL Server的表列表，避免使用SQLAlchemy的inspector"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = 'dbo' ORDER BY TABLE_NAME"
            ))
            return [row[0] for row in result]
    except Exception as e:
        print(f"Error getting tables from SQL Server: {e}")
        return []

def get_sqlserver_columns(engine, table_name):
    """自定义函数，获取SQL Server的列信息，避免使用SQLAlchemy的inspector"""
    columns = []
    try:
        with engine.connect() as connection:
            # 获取列的基本信息
            result = connection.execute(text(
                """SELECT 
                    COLUMN_NAME, 
                    DATA_TYPE, 
                    CASE WHEN IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = :table_name AND TABLE_SCHEMA = 'dbo'
                ORDER BY ORDINAL_POSITION"""
            ), {"table_name": table_name})
            
            for row in result:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': bool(row[2]),
                    'default': row[3]
                })
                
        return columns
    except Exception as e:
        print(f"Error getting columns for table {table_name} from SQL Server: {e}")
        return []

def filter_tables_by_search(table_names, schema_info, search_keyword=None, search_mode='all'):
    """
    根据搜索关键词和搜索模式过滤表
    
    Args:
        table_names: 表名列表
        schema_info: 已提取的表结构信息（用于搜索字段和注释）
        search_keyword: 搜索关键词
        search_mode: 搜索模式 ('all', 'table_name', 'column_name', 'comment', 'table_comment', 'column_comment')
    
    Returns:
        过滤后的表名列表
    """
    if not search_keyword:
        return table_names
    
    search_keyword = search_keyword.lower()
    filtered_tables = []
    
    for table_name in table_names:
        table_info = schema_info.get(table_name, {})
        should_include = False
        
        if search_mode in ['all', 'table_name']:
            # 搜索表名
            if search_keyword in table_name.lower():
                should_include = True
        
        if search_mode in ['all', 'comment', 'table_comment']:
            # 搜索表注释
            table_comment = table_info.get('comment', '').lower()
            if search_keyword in table_comment:
                should_include = True
        
        if search_mode in ['all', 'column_name', 'comment', 'column_comment']:
            # 搜索字段名和字段注释
            for col in table_info.get('columns', []):
                if search_mode in ['all', 'column_name']:
                    if search_keyword in col.get('name', '').lower():
                        should_include = True
                        break
                
                if search_mode in ['all', 'comment', 'column_comment']:
                    if search_keyword in col.get('comment', '').lower():
                        should_include = True
                        break
        
        if should_include:
            filtered_tables.append(table_name)
    
    return filtered_tables

def extract_schema_info(db_config, engine, include_tables=None, exclude_tables=None, search_keyword=None, search_mode='all'):
    """Extracts schema information including table and column comments."""
    inspector = inspect(engine)
    db_type = db_config['type'].lower()
    schema_info = {}

    # 根据数据库类型选择获取表的方法
    if db_type == 'sqlserver':
        table_names = get_sqlserver_tables(engine)
    else:
        table_names = inspector.get_table_names()
    
    # 应用表过滤
    if include_tables:
        table_names = [t for t in table_names if t in include_tables]
    if exclude_tables:
        table_names = [t for t in table_names if t not in exclude_tables]
    
    # 首先提取所有表的基本信息（用于搜索）
    print("正在提取表结构信息用于搜索...")
    for table_name in table_names:
        table_info = {
            'columns': [],
            'comment': ''
        }

        # Get table comment
        if db_type == 'mysql':
            table_info['comment'] = get_table_comments_mysql(inspector, table_name)
        elif db_type == 'postgresql':
            table_info['comment'] = get_table_comments_postgresql(inspector, table_name)
        elif db_type == 'sqlserver':
            table_info['comment'] = get_table_comments_sqlserver(inspector, table_name)
        elif db_type == 'oracle':
            table_info['comment'] = get_table_comments_oracle(inspector, table_name)

        # Get column comments
        column_comments = {}
        if db_type == 'mysql':
            column_comments = get_column_comments_mysql(inspector, table_name)
        elif db_type == 'postgresql':
            column_comments = get_column_comments_postgresql(inspector, table_name)
        elif db_type == 'sqlserver':
            column_comments = get_column_comments_sqlserver(inspector, table_name)
        elif db_type == 'oracle':
            column_comments = get_column_comments_oracle(inspector, table_name)

        # 获取列信息
        if db_type == 'sqlserver':
            columns = get_sqlserver_columns(engine, table_name)
        else:
            columns = inspector.get_columns(table_name)
            
        for col in columns:
            table_info['columns'].append({
                'name': col['name'],
                'type': str(col['type']),
                'nullable': col['nullable'],
                'default': col['default'],
                'comment': column_comments.get(col['name'], '')
            })
        schema_info[table_name] = table_info
    
    # 应用搜索过滤
    if search_keyword:
        print(f"正在应用搜索过滤: 关键词='{search_keyword}', 模式='{search_mode}'")
        original_count = len(table_names)
        table_names = filter_tables_by_search(table_names, schema_info, search_keyword, search_mode)
        filtered_count = len(table_names)
        print(f"搜索结果: 从 {original_count} 个表中筛选出 {filtered_count} 个匹配的表")
        
        # 只保留匹配的表的信息
        filtered_schema_info = {}
        for table_name in table_names:
            filtered_schema_info[table_name] = schema_info[table_name]
        schema_info = filtered_schema_info
    return schema_info

def generate_markdown(schema_info, db_name):
    """Generates data dictionary in Markdown format."""
    markdown_output = f"# 数据库名：{db_name}\n\n"

    for table_name, info in schema_info.items():
        markdown_output += f"## 表名：{table_name}\n\n"
        if info['comment']:
            markdown_output += f"**表注释**：{info['comment']}\n\n"
        markdown_output += "| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |\n"
        markdown_output += "|---|---|---|---|---|\n"
        for col in info['columns']:
            nullable = 'YES' if col['nullable'] else 'NO'
            default = 'NULL' if col['default'] is None else str(col['default'])
            comment = col['comment'] if col['comment'] else ''
            markdown_output += f"| {col['name']} | {col['type']} | {nullable} | {default} | {comment} |\n"
        markdown_output += "\n"
    return markdown_output

def generate_excel(schema_info, db_name, filename, max_tables_per_file=50):
    """
    Generates data dictionary in Excel format.
    
    Args:
        schema_info: Dictionary containing schema information
        db_name: Database name
        filename: Base filename for output
        max_tables_per_file: Maximum number of tables per Excel file
    """
    # 将表分组，每个文件最多包含 max_tables_per_file 个表
    table_names = list(schema_info.keys())
    total_tables = len(table_names)
    file_count = (total_tables + max_tables_per_file - 1) // max_tables_per_file  # 向上取整
    
    for file_idx in range(file_count):
        start_idx = file_idx * max_tables_per_file
        end_idx = min((file_idx + 1) * max_tables_per_file, total_tables)
        current_tables = table_names[start_idx:end_idx]
        
        # 生成文件名
        if file_count > 1:
            output_path = f"{filename}_part{file_idx+1}.xlsx"
        else:
            output_path = f"{filename}.xlsx"
            
        print(f"Creating Excel file {output_path} with {len(current_tables)} tables...")
        
        # 使用不同的写入方式，一次处理一个表
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for table_name in current_tables:
                info = schema_info[table_name]
                df_data = []
                
                if info['comment']:
                    # Add table comment as a row before column headers
                    df_data.append({'字段名': '表注释', '数据类型': '', '可空': '', '默认值': '', '注释': info['comment']})
                    df_data.append({'字段名': '', '数据类型': '', '可空': '', '默认值': '', '注释': ''}) # Empty row for separation

                for col in info['columns']:
                    nullable = 'YES' if col['nullable'] else 'NO'
                    default = 'NULL' if col['default'] is None else str(col['default'])
                    comment = col['comment'] if col['comment'] else ''
                    df_data.append({
                        '字段名': col['name'],
                        '数据类型': col['type'],
                        '可空': nullable,
                        '默认值': default,
                        '注释': comment
                    })
                    
                # 创建 DataFrame 并写入到 Excel
                df = pd.DataFrame(df_data)
                
                # 处理表名过长的情况
                sheet_name = table_name[:31]
                if len(table_name) > 31:
                    print(f"Warning: Table name '{table_name}' truncated to '{sheet_name}' for Excel compatibility")
                    
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 清理内存
                del df
                del df_data
                
        print(f"Generated Excel file: {output_path}")
        
    return file_count

def generate_interactive_html(schema_info, db_name, filename):
    """
    Generates an interactive HTML data dictionary with search functionality.
    All tables are included in a single file with JavaScript-based search and filtering.
    
    Args:
        schema_info: Dictionary containing schema information
        db_name: Database name
        filename: Base filename for output
    """
    # 创建输出文件夹
    output_dir = f"{filename}_interactive"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "index.html")
    print(f"Creating interactive HTML data dictionary: {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as html_file:
        # HTML 头部和 CSS
        html_file.write(f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>数据字典 - {db_name}</title>
            <style>
                /* 基本样式 */
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                
                /* 导航栏样式 */
                .navbar {{ background-color: #34495e; color: white; padding: 15px 0; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .navbar-content {{ display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
                .navbar h1 {{ margin: 0; font-size: 1.5rem; color: white; }}
                
                /* 搜索栏样式 */
                .search-container {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
                #searchInput {{ padding: 8px 15px; border: none; border-radius: 4px; width: 300px; font-size: 16px; }}
                #searchMode {{ padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; background-color: white; }}
                #tableCount {{ margin-left: 15px; font-size: 0.9rem; }}
                .search-help {{ font-size: 0.8rem; color: #ccc; margin-left: 10px; }}
                
                /* 主内容区域样式 */
                .main-content {{ display: flex; margin-top: 20px; }}
                
                /* 表列表样式 */
                .table-list {{ width: 300px; height: calc(100vh - 130px); overflow-y: auto; padding-right: 20px; position: sticky; top: 80px; }}
                .table-list ul {{ list-style-type: none; padding: 0; margin: 0; }}
                .table-list li {{ padding: 8px 10px; border-bottom: 1px solid #eee; cursor: pointer; transition: background-color 0.2s; }}
                .table-list li:hover {{ background-color: #f5f5f5; }}
                .table-list li.active {{ background-color: #e0f7fa; border-left: 4px solid #26a69a; padding-left: 6px; }}
                
                /* 表详情样式 */
                .table-details {{ flex: 1; padding-left: 30px; border-left: 1px solid #eee; min-height: calc(100vh - 130px); }}
                .table-comment {{ font-style: italic; margin-bottom: 15px; color: #555; }}
                
                /* 表格样式 */
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px 15px; text-align: left; }}
                th {{ background-color: #f8f9fa; position: sticky; top: 80px; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                tr:hover {{ background-color: #f1f1f1; }}
                
                /* 字段高亮 */
                .highlight {{ background-color: #fff9c4; }}
                
                /* 响应式设计 */
                @media (max-width: 768px) {{
                    .main-content {{ flex-direction: column; }}
                    .table-list {{ width: 100%; height: auto; max-height: 300px; padding-right: 0; margin-bottom: 20px; }}
                    .table-details {{ padding-left: 0; border-left: none; }}
                    .search-container {{ flex-direction: column; align-items: stretch; gap: 5px; }}
                    #searchInput {{ width: 100%; }}
                    #searchMode {{ width: 100%; }}
                    .search-help {{ margin-left: 0; text-align: center; }}
                }}
                
                /* 加载中样式 */
                .loading {{ display: flex; justify-content: center; align-items: center; height: 100px; }}
                .loading::after {{ content: "加载中..."; color: #666; }}
                
                /* 没有结果样式 */
                .no-results {{ text-align: center; padding: 50px; color: #666; }}
                
                /* 返回顶部按钮 */
                .back-to-top {{ position: fixed; bottom: 20px; right: 20px; background-color: #34495e; color: white; border: none; border-radius: 50%; width: 50px; height: 50px; text-align: center; line-height: 50px; cursor: pointer; opacity: 0.7; transition: opacity 0.3s; display: none; }}
                .back-to-top:hover {{ opacity: 1; }}
            </style>
        </head>
        <body>
            <!-- 导航栏 -->
            <div class="navbar">
                <div class="navbar-content">
                    <h1>数据字典 - {db_name}</h1>
                    <div class="search-container">
                        <input type="text" id="searchInput" placeholder="输入搜索关键词..." />
                        <select id="searchMode">
                            <option value="all">所有内容</option>
                            <option value="table_name">仅表名</option>
                            <option value="column_name">仅字段名</option>
                            <option value="comment">所有注释</option>
                            <option value="table_comment">仅表注释</option>
                            <option value="column_comment">仅字段注释</option>
                        </select>
                        <span id="tableCount">共 {len(schema_info)} 个表</span>
                        <span class="search-help">选择搜索范围以精确筛选</span>
                    </div>
                </div>
            </div>
            
            <div class="container">
                <div class="main-content">
                    <!-- 表列表 -->
                    <div class="table-list">
                        <h2>所有表</h2>
                        <ul id="tableList"></ul>
                    </div>
                    
                    <!-- 表详情 -->
                    <div class="table-details" id="tableDetails">
                        <div class="no-results">请从左侧选择一个表或使用搜索框进行搜索</div>
                    </div>
                </div>
            </div>
            
            <!-- 返回顶部按钮 -->
            <button class="back-to-top" id="backToTop" title="返回顶部">↑</button>
            
            <!-- 数据脚本 -->
            <script>
            // 数据字典数据
            const schemaData = 
        ''')
        
        # 将数据字典数据转换为 JavaScript 对象
        import json
        
        # 准备数据字典数据
        schema_data_dict = {}
        for table_name, info in schema_info.items():
            columns_data = []
            for col in info['columns']:
                nullable = 'YES' if col['nullable'] else 'NO'
                default = 'NULL' if col['default'] is None else str(col['default'])
                comment = col['comment'] if col['comment'] else ''
                columns_data.append({
                    'name': col['name'],
                    'type': col['type'],
                    'nullable': nullable,
                    'default': default,
                    'comment': comment
                })
            
            schema_data_dict[table_name] = {
                'comment': info['comment'] if info['comment'] else '',
                'columns': columns_data
            }
        
        # 使用json模块正确处理Unicode字符和特殊字符
        schema_json = json.dumps(schema_data_dict, ensure_ascii=False, indent=2)
        
        # 写入JSON数据
        html_file.write(schema_json)
        
        html_file.write('''
        ;
            
            // DOM 元素
            const searchInput = document.getElementById('searchInput');
            const searchMode = document.getElementById('searchMode');
            const tableList = document.getElementById('tableList');
            const tableDetails = document.getElementById('tableDetails');
            const backToTop = document.getElementById('backToTop');
            const tableCount = document.getElementById('tableCount');
            
            // 当前选中的表
            let currentTable = null;
            
            // 初始化表列表
            function initializeTableList() {
                const tableNames = Object.keys(schemaData).sort();
                tableList.innerHTML = '';
                
                tableNames.forEach(tableName => {
                    const li = document.createElement('li');
                    li.textContent = tableName;
                    li.setAttribute('data-table', tableName);
                    li.addEventListener('click', () => showTableDetails(tableName));
                    tableList.appendChild(li);
                });
            }
            
            // 显示表详情
            function showTableDetails(tableName, highlightText = '') {
                // 更新当前选中的表
                currentTable = tableName;
                
                // 更新列表选中状态
                const allItems = tableList.querySelectorAll('li');
                allItems.forEach(item => item.classList.remove('active'));
                const activeItem = tableList.querySelector(`li[data-table="${tableName}"]`);
                if (activeItem) {
                    activeItem.classList.add('active');
                    activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
                
                const tableData = schemaData[tableName];
                if (!tableData) return;
                
                let html = `<h2>${tableName}</h2>`;
                
                if (tableData.comment) {
                    html += `<p class="table-comment"><strong>表注释：</strong> ${tableData.comment}</p>`;
                }
                
                html += `
                <table>
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>数据类型</th>
                            <th>可空</th>
                            <th>默认值</th>
                            <th>注释</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                
                tableData.columns.forEach(col => {
                    // 如果有搜索文本，高亮匹配的内容
                    let nameCell = col.name;
                    let commentCell = col.comment || '';
                    
                    if (highlightText) {
                        const regex = new RegExp(`(${highlightText})`, 'gi');
                        nameCell = nameCell.replace(regex, '<span class="highlight">$1</span>');
                        commentCell = commentCell.replace(regex, '<span class="highlight">$1</span>');
                    }
                    
                    html += `
                        <tr>
                            <td>${nameCell}</td>
                            <td>${col.type}</td>
                            <td>${col.nullable}</td>
                            <td>${col.default}</td>
                            <td>${commentCell}</td>
                        </tr>
                    `;
                });
                
                html += `
                    </tbody>
                </table>
                `;
                
                tableDetails.innerHTML = html;
            }
            
            // 搜索功能
            function searchTables(query, mode = 'all') {
                if (!query) {
                    // 如果搜索框为空，显示所有表
                    initializeTableList();
                    tableCount.textContent = `共 ${Object.keys(schemaData).length} 个表`;
                    if (currentTable) {
                        showTableDetails(currentTable);
                    } else {
                        tableDetails.innerHTML = '<div class="no-results">请从左侧选择一个表或使用搜索框进行搜索</div>';
                    }
                    return;
                }
                
                const tableNames = Object.keys(schemaData);
                const matchedTables = [];
                const queryLower = query.toLowerCase();
                
                // 根据搜索模式进行搜索
                tableNames.forEach(tableName => {
                    const tableData = schemaData[tableName];
                    let shouldInclude = false;
                    
                    // 搜索表名
                    if (mode === 'all' || mode === 'table_name') {
                        if (tableName.toLowerCase().includes(queryLower)) {
                            shouldInclude = true;
                        }
                    }
                    
                    // 搜索表注释
                    if ((mode === 'all' || mode === 'comment' || mode === 'table_comment') && !shouldInclude) {
                        if (tableData.comment && tableData.comment.toLowerCase().includes(queryLower)) {
                            shouldInclude = true;
                        }
                    }
                    
                    // 搜索字段名和字段注释
                    if ((mode === 'all' || mode === 'column_name' || mode === 'comment' || mode === 'column_comment') && !shouldInclude) {
                        for (const col of tableData.columns) {
                            // 搜索字段名
                            if ((mode === 'all' || mode === 'column_name') && col.name.toLowerCase().includes(queryLower)) {
                                shouldInclude = true;
                                break;
                            }
                            
                            // 搜索字段注释
                            if ((mode === 'all' || mode === 'comment' || mode === 'column_comment') && 
                                col.comment && col.comment.toLowerCase().includes(queryLower)) {
                                shouldInclude = true;
                                break;
                            }
                        }
                    }
                    
                    if (shouldInclude) {
                        matchedTables.push(tableName);
                    }
                });
                
                // 更新表列表
                tableList.innerHTML = '';
                if (matchedTables.length > 0) {
                    matchedTables.sort().forEach(tableName => {
                        const li = document.createElement('li');
                        li.textContent = tableName;
                        li.setAttribute('data-table', tableName);
                        li.addEventListener('click', () => showTableDetails(tableName, query));
                        tableList.appendChild(li);
                    });
                    
                    // 更新表计数
                    tableCount.textContent = `找到 ${matchedTables.length} 个匹配的表`;
                    
                    // 自动显示第一个匹配的表
                    showTableDetails(matchedTables[0], query);
                } else {
                    tableCount.textContent = '没有找到匹配的表';
                    tableDetails.innerHTML = '<div class="no-results">没有找到匹配的表或字段</div>';
                }
            }
            
            // 滚动事件处理
            window.addEventListener('scroll', () => {
                if (window.pageYOffset > 300) {
                    backToTop.style.display = 'block';
                } else {
                    backToTop.style.display = 'none';
                }
            });
            
            // 返回顶部按钮点击事件
            backToTop.addEventListener('click', () => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
            
            // 搜索框输入事件
            searchInput.addEventListener('input', (e) => {
                searchTables(e.target.value.trim(), searchMode.value);
            });
            
            // 搜索模式改变事件
            searchMode.addEventListener('change', (e) => {
                searchTables(searchInput.value.trim(), e.target.value);
            });
            
            // 初始化
            document.addEventListener('DOMContentLoaded', () => {
                initializeTableList();
            });
            
            // 页面加载完成后初始化
            initializeTableList();
            </script>
        </body>
        </html>
        ''')
    
    print(f"Generated interactive HTML data dictionary: {output_path}")
    print(f"Open this file in a web browser to view and search the data dictionary.")
    return output_path

def generate_html(schema_info, db_name, filename, max_tables_per_file=100):
    """
    Generates data dictionary in HTML format.
    
    Args:
        schema_info: Dictionary containing schema information
        db_name: Database name
        filename: Base filename for output
        max_tables_per_file: Maximum number of tables per HTML file
    """
    # 创建输出文件夹
    output_dir = f"{filename}_html"
    os.makedirs(output_dir, exist_ok=True)
    
    # 将表分组，每个文件最多包含 max_tables_per_file 个表
    table_names = list(schema_info.keys())
    total_tables = len(table_names)
    file_count = (total_tables + max_tables_per_file - 1) // max_tables_per_file  # 向上取整
    
    # 创建目录页
    if file_count > 1:
        index_path = os.path.join(output_dir, "index.html")
        with open(index_path, 'w', encoding='utf-8') as index_file:
            index_file.write(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>数据字典 - {db_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    ul {{ list-style-type: none; padding: 0; }}
                    li {{ margin: 10px 0; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <h1>数据字典 - {db_name}</h1>
                <h2>目录</h2>
                <ul>
            ''')
            
            for file_idx in range(file_count):
                part_filename = f"part{file_idx+1}.html"
                start_idx = file_idx * max_tables_per_file
                end_idx = min((file_idx + 1) * max_tables_per_file, total_tables)
                index_file.write(f'<li><a href="{part_filename}">第 {file_idx+1} 部分 (表 {start_idx+1} - {end_idx})</a></li>\n')
                
            index_file.write('''
                </ul>
            </body>
            </html>
            ''')
        print(f"Generated HTML index file: {index_path}")
    
    # 生成各部分文件
    for file_idx in range(file_count):
        start_idx = file_idx * max_tables_per_file
        end_idx = min((file_idx + 1) * max_tables_per_file, total_tables)
        current_tables = table_names[start_idx:end_idx]
        
        # 生成文件名
        if file_count > 1:
            output_path = os.path.join(output_dir, f"part{file_idx+1}.html")
        else:
            output_path = os.path.join(output_dir, "index.html")
            
        print(f"Creating HTML file {output_path} with {len(current_tables)} tables...")
        
        with open(output_path, 'w', encoding='utf-8') as html_file:
            # HTML 头部
            html_file.write(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>数据字典 - {db_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .table-comment {{ font-style: italic; margin-bottom: 10px; }}
                    .table-of-contents {{ margin-bottom: 30px; }}
                    .back-to-top {{ margin-bottom: 20px; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <h1>数据字典 - {db_name}</h1>
            ''')
            
            # 如果有多个文件，添加返回目录的链接
            if file_count > 1:
                html_file.write(f'<p><a href="{os.path.basename(filename)}_index.html">返回目录</a></p>\n')
            
            # 添加当前文件的目录
            html_file.write('''
                <div class="table-of-contents">
                    <h2>本页内容</h2>
                    <ul>
            ''')
            
            for table_name in current_tables:
                html_file.write(f'<li><a href="#{table_name}">{table_name}</a></li>\n')
                
            html_file.write('''
                    </ul>
                </div>
            ''')
            
            # 生成每个表的 HTML
            for table_name in current_tables:
                info = schema_info[table_name]
                
                html_file.write(f'<div id="{table_name}">\n')
                html_file.write(f'<h2>{table_name}</h2>\n')
                
                if info['comment']:
                    html_file.write(f'<p class="table-comment"><strong>表注释：</strong> {info["comment"]}</p>\n')
                
                html_file.write('''
                <table>
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>数据类型</th>
                            <th>可空</th>
                            <th>默认值</th>
                            <th>注释</th>
                        </tr>
                    </thead>
                    <tbody>
                ''')
                
                for col in info['columns']:
                    nullable = 'YES' if col['nullable'] else 'NO'
                    default = 'NULL' if col['default'] is None else str(col['default'])
                    comment = col['comment'] if col['comment'] else ''
                    
                    html_file.write(f'''
                        <tr>
                            <td>{col['name']}</td>
                            <td>{col['type']}</td>
                            <td>{nullable}</td>
                            <td>{default}</td>
                            <td>{comment}</td>
                        </tr>
                    ''')
                
                html_file.write('''
                    </tbody>
                </table>
                ''')
                
                html_file.write('<p class="back-to-top"><a href="#">返回顶部</a></p>\n')
                html_file.write('</div>\n')
            
            # HTML 尾部
            html_file.write('''
            </body>
            </html>
            ''')
        
        print(f"Generated HTML file: {output_path}")
    
    return file_count

def generate_csv(schema_info, db_name, filename):
    """Generates data dictionary in CSV format (one CSV per table)."""
    output_dir = f"{filename}_csvs"
    os.makedirs(output_dir, exist_ok=True)

    for table_name, info in schema_info.items():
        csv_path = os.path.join(output_dir, f"{table_name}.csv")
        df_data = []
        if info['comment']:
            df_data.append({'字段名': '表注释', '数据类型': '', '可空': '', '默认值': '', '注释': info['comment']})
            df_data.append({'字段名': '', '数据类型': '', '可空': '', '默认值': '', '注释': ''})

        for col in info['columns']:
            nullable = 'YES' if col['nullable'] else 'NO'
            default = 'NULL' if col['default'] is None else str(col['default'])
            comment = col['comment'] if col['comment'] else ''
            df_data.append({
                '字段名': col['name'],
                '数据类型': col['type'],
                '可空': nullable,
                '默认值': default,
                '注释': comment
            })
        df = pd.DataFrame(df_data)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"Generated CSV file for table {table_name}: {csv_path}")
    print(f"Generated CSV files in directory: {output_dir}")

def read_incremental_tables_file(file_path):
    """读取增量表文件，返回表名列表"""
    if not os.path.exists(file_path):
        return []
    
    tables = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith('#'):
                    tables.append(line)
        return tables
    except Exception as e:
        print(f"Error reading incremental tables file {file_path}: {e}")
        return []

def show_incremental_file_content(file_path):
    """显示增量表文件内容"""
    if not os.path.exists(file_path):
        print(f"增量表文件 '{file_path}' 不存在")
        print("您可以创建此文件并添加需要更新的表名，每行一个表名")
        print("\n示例内容:")
        print("# 增量更新表列表")
        print("# 格式：每行一个表名，# 开头为注释")
        print("user_info")
        print("order_detail")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"增量表文件 '{file_path}' 内容:")
        print("-" * 50)
        if content.strip():
            print(content)
        else:
            print("(文件为空)")
        print("-" * 50)
        
        # 解析并显示有效的表名
        tables = read_incremental_tables_file(file_path)
        if tables:
            print(f"\n有效的表名 ({len(tables)} 个):")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
        else:
            print("\n没有找到有效的表名")
            
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")

def clear_incremental_file(file_path):
    """清空增量表文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 增量更新表列表\n")
            f.write("# 格式：每行一个表名，# 开头为注释\n")
            f.write("\n")
        print(f"已清空增量表文件 '{file_path}'")
    except Exception as e:
        print(f"Error clearing file {file_path}: {e}")

def get_incremental_tables(args):
    """获取增量同步的表列表"""
    if args.tables:
        # 命令行指定的表优先
        tables = [table.strip() for table in args.tables.split(',') if table.strip()]
        print(f"使用命令行指定的表: {tables}")
        return tables
    else:
        # 从文件读取
        tables = read_incremental_tables_file(args.tables_file)
        if tables:
            print(f"从文件 '{args.tables_file}' 读取到 {len(tables)} 个表")
            print(f"表列表: {tables}")
        else:
            print(f"增量表文件 '{args.tables_file}' 为空或不存在")
            print("请在文件中添加需要更新的表名，或使用 --tables 参数直接指定")
        return tables

def save_incremental_state(state_file, schema_info, db_name, db_host, db_port, db_user, updated_tables_list=None):
    """保存增量同步状态"""
    import datetime
    
    # 如果未提供更新列表，则默认为所有表（用于兼容旧逻辑或全量同步场景）
    if updated_tables_list is None:
        updated_tables_list = list(schema_info.keys())

    state = {
        'last_sync': datetime.datetime.now().isoformat(),
        'database': {
            'name': db_name,
            'host': db_host,
            'port': db_port,
            'user': db_user
        },
        'tables_count': len(schema_info),  # 文档中包含的总表数
        'tables': list(schema_info.keys()), # 文档中包含的所有表的列表
        'updated_tables': updated_tables_list  # 本次实际更新的表
    }
    
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存增量同步状态到 '{state_file}'")
        print(f"  数据库: {db_host}:{db_port}/{db_name}")
        print(f"  更新表数: {len(updated_tables_list)}") # 修正日志输出，只显示本次更新的数量
    except Exception as e:
        print(f"Warning: Could not save incremental state: {e}")

def load_incremental_state(state_file):
    """加载增量同步状态"""
    if not os.path.exists(state_file):
        return None
    
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            import json
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load incremental state: {e}")
        return None

def show_incremental_status(config, output_filename_base):
    """显示增量同步状态"""
    # 状态文件现在保存在交互式HTML的输出目录中
    state_file = os.path.join(f"{output_filename_base}_interactive", f"{output_filename_base}_incremental_state.json")
    
    print(f"增量同步状态检查:")
    print(f"状态文件: {state_file}")
    print("-" * 60)
    
    # 当前配置信息
    db_name = config['database']['database']
    db_host = config['database']['host']
    db_port = config['database']['port']
    db_user = config['database']['user']
    
    print(f"当前配置:")
    print(f"  数据库: {db_host}:{db_port}/{db_name}")
    print(f"  用户: {db_user}")
    print()
    
    # 加载状态文件
    state = load_incremental_state(state_file)
    
    if not state:
        print("❌ 没有找到增量同步状态文件")
        print("这可能是因为:")
        print("1. 从未运行过增量同步")
        print("2. 状态文件被删除")
        print("3. 使用了不同的输出文件名")
        return
    
    print(f"上次增量同步:")
    print(f"  时间: {state.get('last_sync', 'Unknown')}")
    
    # 检查数据库信息匹配
    state_db = state.get('database', {})
    if isinstance(state_db, str):
        # 兼容旧格式
        state_db_name = state_db
        state_db_host = "Unknown"
        state_db_port = "Unknown"
    else:
        state_db_name = state_db.get('name', 'Unknown')
        state_db_host = state_db.get('host', 'Unknown')
        state_db_port = state_db.get('port', 'Unknown')
    
    print(f"  数据库: {state_db_host}:{state_db_port}/{state_db_name}")
    print(f"  表总数: {state.get('tables_count', 0)}")
    
    updated_tables = state.get('updated_tables', state.get('tables', []))
    print(f"  上次更新表数: {len(updated_tables)}")
    
    # 验证数据库匹配
    db_match = (state_db_name == db_name and 
                state_db_host == db_host and 
                str(state_db_port) == str(db_port))
    
    if db_match:
        print("✓ 数据库配置匹配")
    else:
        print("⚠️  数据库配置不匹配!")
        print("   这可能导致增量同步到错误的文件")
        print("   建议:")
        print("   1. 检查配置文件是否正确")
        print("   2. 确认要更新的数据库")
        print("   3. 考虑使用不同的输出文件名")
    
    # 检查目标HTML文件
    html_file = os.path.join(f"{output_filename}_interactive", "index.html")
    print(f"\n目标HTML文件: {html_file}")
    
    if os.path.exists(html_file):
        print("✓ 目标HTML文件存在")
        
        # 验证HTML文件数据库匹配
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            if validate_html_database_match(html_content, db_name):
                print("✓ HTML文件数据库匹配")
            else:
                print("⚠️  HTML文件数据库不匹配")
        except Exception as e:
            print(f"❌ 无法验证HTML文件: {e}")
    else:
        print("❌ 目标HTML文件不存在")
        print("   增量同步将创建新文件")
    
    print("\n" + "=" * 60)

def merge_schema_info_incremental(existing_schema_file, new_schema_info, output_format, db_name, db_host):
    """将新的表信息合并到现有的schema信息中"""
    if not os.path.exists(existing_schema_file):
        print("没有找到现有的数据字典文件，将创建新文件")
        return new_schema_info
    
    if output_format == 'interactive-html':
        # 对于交互式HTML，需要从现有文件中提取JSON数据
        return merge_interactive_html_data(existing_schema_file, new_schema_info, db_name, db_host)
    else:
        # 对于其他格式，暂时返回新数据（后续可以扩展）
        print(f"增量更新暂不支持 {output_format} 格式的合并，将覆盖现有文件")
        return new_schema_info

def validate_html_database_match(html_content, db_name):
    """验证HTML文件是否属于指定的数据库"""
    try:
        # 查找HTML标题中的数据库名
        title_pattern = f"<title>数据字典 - {db_name}</title>"
        if title_pattern in html_content:
            return True
        
        # 查找H1标签中的数据库名
        h1_pattern = f"<h1>数据字典 - {db_name}</h1>"
        if h1_pattern in html_content:
            return True
        
        # 如果都没找到，可能是数据库名不匹配
        return False
        
    except Exception as e:
        print(f"Warning: Could not validate database match: {e}")
        return True  # 验证失败时默认允许合并

def merge_interactive_html_data(html_file, new_schema_info, db_name, db_host):
    """从现有的交互式HTML文件中提取数据并合并新数据"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证HTML文件是否属于当前数据库
        if not validate_html_database_match(content, db_name):
            print(f"警告: 现有HTML文件不属于当前数据库 '{db_name}'")
            print("这可能是因为:")
            print("1. 配置文件指向了不同的数据库")
            print("2. 数据库名称发生了变化")
            print("3. 使用了错误的配置文件")
            
            user_choice = input("是否继续合并? (y/N): ").strip().lower()
            if user_choice not in ['y', 'yes']:
                print("取消合并，将创建新的数据字典文件")
                return new_schema_info
        
        # 查找JSON数据的开始和结束位置
        start_marker = "const schemaData = "
        end_marker = ";"
        
        start_pos = content.find(start_marker)
        if start_pos == -1:
            print("Warning: Could not find schema data in existing HTML file")
            return new_schema_info
        
        start_pos += len(start_marker)
        
        # 从start_pos开始查找第一个分号，但要考虑JSON中可能包含分号
        # 更安全的方法是查找 "; \n" 或类似的模式
        temp_content = content[start_pos:]
        brace_count = 0
        end_pos = -1
        
        for i, char in enumerate(temp_content):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # 找到JSON结束位置
                    end_pos = i + 1
                    break
        
        if end_pos == -1:
            print("Warning: Could not parse schema data from existing HTML file")
            return new_schema_info
        
        json_str = temp_content[:end_pos]
        
        import json
        existing_schema_info = json.loads(json_str)
        
        # 合并数据：新数据覆盖现有数据
        merged_schema_info = existing_schema_info.copy()
        merged_schema_info.update(new_schema_info)
        
        print(f"✓ 成功合并数据：现有 {len(existing_schema_info)} 个表，新增/更新 {len(new_schema_info)} 个表，合并后共 {len(merged_schema_info)} 个表")
        
        return merged_schema_info
        
    except Exception as e:
        print(f"Warning: Could not merge with existing HTML file: {e}")
        print("将创建新的数据字典文件")
        return new_schema_info

def test_db_connection(db_config):
    """Tests the database connection."""
    try:
        db_connection_string = get_db_connection_string(db_config)
        engine = create_engine(db_connection_string)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")) # Simple query to test connection
        print(f"Successfully connected to database: {db_config['database']} ({db_config['type']})")
        return True
    except Exception as e:
        print(f"Error connecting to database: {db_config['database']} ({db_config['type']})")
        print(f"Details: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate data dictionary from database.')
    parser.add_argument('--config', type=str, default='config.ini', help='Path to config file.')
    parser.add_argument('--env', type=str, help='Database environment to use (for multi-environment config).')
    parser.add_argument('--list-env', action='store_true', help='List available environments in the config file and exit.')
    parser.add_argument('--test-connection', action='store_true', help='Test database connection and exit.')
    parser.add_argument('--include-tables', type=str, help='Comma-separated list of tables to include. If not specified, all tables will be included.')
    parser.add_argument('--exclude-tables', type=str, help='Comma-separated list of tables to exclude.')
    parser.add_argument('--search-keyword', type=str, help='Search keyword to filter tables and columns.')
    parser.add_argument('--search-mode', type=str, default='all', 
                       choices=['all', 'table_name', 'column_name', 'comment', 'table_comment', 'column_comment'],
                       help='Search mode: all (default), table_name (only table names), column_name (only column names), comment (all comments), table_comment (only table comments), column_comment (only column comments).')
    parser.add_argument('--incremental', action='store_true', help='Enable incremental sync mode.')
    parser.add_argument('--tables-file', type=str, default='incremental_tables.txt', help='File containing list of tables to update in incremental mode (default: incremental_tables.txt).')
    parser.add_argument('--tables', type=str, help='Comma-separated list of tables to update in incremental mode (overrides --tables-file).')
    parser.add_argument('--show-incremental-file', action='store_true', help='Show the content of incremental tables file and exit.')
    parser.add_argument('--clear-incremental-file', action='store_true', help='Clear the incremental tables file and exit.')
    parser.add_argument('--show-incremental-status', action='store_true', help='Show the incremental sync status and exit.')
    parser.add_argument('--output-format', type=str, help='Override output format from config (markdown, excel, csv, html, interactive-html).')
    parser.add_argument('--output-file', type=str, help='Override output filename from config.')
    parser.add_argument('--max-tables-per-file', type=int, default=50, help='Maximum number of tables per file for Excel and HTML output.')
    args = parser.parse_args()
    
    # 处理增量同步相关的命令
    if args.show_incremental_file:
        show_incremental_file_content(args.tables_file)
        return
    
    if args.clear_incremental_file:
        clear_incremental_file(args.tables_file)
        return
    
    if args.show_incremental_status:
        # 需要先读取配置来获取数据库信息
        try:
            config = read_config(args.config, args.env)
            
            # 确定输出文件名
            if args.output_file:
                output_filename = args.output_file
            else:
                if 'filename' in config['output'] and config['output']['filename'].strip():
                    output_filename = config['output']['filename']
                else:
                    host_clean = config['database']['host'].replace('.', '_')
                    db_clean = config['database']['database'].replace('.', '_')
                    output_filename = f"{host_clean}_{db_clean}"
            
            show_incremental_status(config, output_filename)
        except Exception as e:
            print(f"Error reading config: {e}")
        return
    
    # 如果指定了列出环境选项，则列出可用环境并退出
    if args.list_env:
        if list_environments is None:
            print("错误: 未找到多环境配置支持模块 multi_db_support.py")
            return
            
        try:
            environments, default_env = list_environments(args.config)
            if environments:
                print(f"配置文件 '{args.config}' 中的可用环境:")
                for env in environments:
                    if env == default_env:
                        print(f"  - {env} (默认)")
                    else:
                        print(f"  - {env}")
            else:
                print(f"配置文件 '{args.config}' 不是多环境配置文件或未定义任何环境")
        except Exception as e:
            print(f"列出环境时出错: {e}")
        return

    try:
        # 读取配置，支持环境参数
        config = read_config(args.config, args.env)
        db_type = config['database']['type']
        db_name = config['database']['database']
        db_host = config['database']['host']
        
        # 如果使用了环境参数，显示当前环境信息
        if args.env:
            print(f"使用环境: {args.env}")
            print(f"数据库: {db_host}:{config['database']['port']}/{db_name}")
            print(f"用户: {config['database']['user']}\n")
        
        # 获取输出格式和文件名
        output_format = args.output_format if args.output_format else config['output']['format']
        
        # 如果用户没有指定输出文件名，则使用host和database组合
        if args.output_file:
            output_filename = args.output_file
        else:
            # 从配置文件获取文件名，如果未指定则使用host_database格式
            if 'filename' in config['output'] and config['output']['filename'].strip():
                output_filename = config['output']['filename']
            else:
                # 清理主机名和数据库名，移除特殊字符
                host_clean = db_host.replace('.', '_')
                db_clean = db_name.replace('.', '_')
                output_filename = f"{host_clean}_{db_clean}"

        # 测试数据库连接
        if args.test_connection:
            if test_db_connection(config['database']):
                print("Database connection test passed.")
            else:
                print("Database connection test failed.")
            return # Exit after testing connection

        # 处理表过滤参数
        include_tables = args.include_tables.split(',') if args.include_tables else None
        exclude_tables = args.exclude_tables.split(',') if args.exclude_tables else None
        
        # 处理增量同步
        incremental_tables = None
        if args.incremental:
            incremental_tables = get_incremental_tables(args)
            if not incremental_tables:
                print("错误: 增量同步模式下没有指定要更新的表")
                print(f"请在 '{args.tables_file}' 文件中添加表名，或使用 --tables 参数指定")
                return
            
            # 在增量模式下，include_tables 应该是增量表列表
            include_tables = incremental_tables
            print(f"增量同步模式：将更新 {len(incremental_tables)} 个表")

        # 连接数据库并提取信息
        db_connection_string = get_db_connection_string(config['database'])
        engine = create_engine(db_connection_string)

        print(f"Connecting to database: {db_name} ({db_type})...")
        
        # 显示搜索信息
        if args.search_keyword:
            print(f"搜索关键词: '{args.search_keyword}'")
            print(f"搜索模式: {args.search_mode}")
            search_mode_descriptions = {
                'all': '所有内容（表名、字段名、注释）',
                'table_name': '仅表名',
                'column_name': '仅字段名',
                'comment': '所有注释（表注释和字段注释）',
                'table_comment': '仅表注释',
                'column_comment': '仅字段注释'
            }
            print(f"搜索范围: {search_mode_descriptions.get(args.search_mode, args.search_mode)}")
        
        schema_info = extract_schema_info(config['database'], engine, include_tables, exclude_tables, 
                                        args.search_keyword, args.search_mode)
        print("Schema information extracted successfully.")

        # 计算表的数量和确认每个文件的最大表数
        max_tables_per_file = args.max_tables_per_file

        # 计算表的数量
        table_count = len(schema_info)
        print(f"Found {table_count} tables in database {db_name}")
        
        # 处理增量合并
        if args.incremental and output_format == 'interactive-html':
            # 确定现有文件路径
            existing_file_path = os.path.join(f"{output_filename}_interactive", "index.html")
            
            print(f"增量同步目标:")
            print(f"  数据库: {db_host}:{config['database']['port']}/{db_name}")
            print(f"  目标文件: {existing_file_path}")
            
            # 合并现有数据
            schema_info = merge_schema_info_incremental(existing_file_path, schema_info, output_format, db_name, db_host)
            
            # 更新表计数
            table_count = len(schema_info)
            print(f"合并后共有 {table_count} 个表")

        # 生成数据字典
        if output_format == 'markdown':
            # 如果表的数量过多，建议使用其他格式
            if table_count > 100:
                print(f"Warning: Large number of tables ({table_count}). Markdown may be slow to render. Consider using HTML or Excel format.")
            
            markdown_output = generate_markdown(schema_info, db_name)
            output_path = f"{output_filename}.md"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            print(f"Generated Markdown file: {output_path}")
            
        elif output_format == 'excel':
            file_count = generate_excel(schema_info, db_name, output_filename, max_tables_per_file)
            if file_count > 1:
                print(f"Due to the large number of tables, data dictionary was split into {file_count} Excel files.")
                
        elif output_format == 'html':
            file_count = generate_html(schema_info, db_name, output_filename, max_tables_per_file)
            output_dir = f"{output_filename}_html"
            if file_count > 1:
                print(f"Due to the large number of tables, data dictionary was split into {file_count} HTML files.")
                print(f"Open {os.path.join(output_dir, 'index.html')} to view the data dictionary.")
            else:
                print(f"Open {os.path.join(output_dir, 'index.html')} to view the data dictionary.")
                
        elif output_format == 'interactive-html':
            output_path = generate_interactive_html(schema_info, db_name, output_filename)
            print(f"\n推荐使用: 交互式HTML数据字典已生成，可以通过浏览器打开并使用搜索功能快速查找表和字段。")
            print(f"打开 {output_path} 查看数据字典。")
            print(f"\n注意: 所有文件已生成在 {os.path.dirname(output_path)} 文件夹中。")
                
        elif output_format == 'csv':
            generate_csv(schema_info, db_name, output_filename)
            
        else:
            print(f"Unsupported output format: {output_format}")
            print("Supported formats: markdown, excel, html, interactive-html, csv")
            print("\n推荐使用 interactive-html 格式，它提供了搜索功能，方便查找表和字段。")
            print("例如: python generate_data_dictionary.py --output-format interactive-html")
            
        # 显示搜索功能使用提示
        if args.search_keyword:
            print(f"\n搜索功能使用提示:")
            print(f"- 您可以使用 --search-keyword 参数来过滤表")
            print(f"- 使用 --search-mode 参数来指定搜索范围:")
            print(f"  * all: 搜索所有内容（默认）")
            print(f"  * table_name: 仅搜索表名")
            print(f"  * column_name: 仅搜索字段名")
            print(f"  * comment: 搜索所有注释")
            print(f"  * table_comment: 仅搜索表注释")
            print(f"  * column_comment: 仅搜索字段注释")
            print(f"- 交互式HTML格式提供了更强大的在线搜索功能")
        
        # 保存增量同步状态
        if args.incremental:
            # 将状态文件保存到交互式HTML的输出目录中，方便管理
            output_dir = f"{output_filename}_interactive"
            state_file = os.path.join(output_dir, f"{output_filename}_incremental_state.json")
            save_incremental_state(
                state_file, 
                schema_info, 
                db_name, 
                db_host, 
                config['database']['port'], 
                config['database']['user'],
                updated_tables_list=incremental_tables
            )
            
        print("Data dictionary generation completed successfully.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
