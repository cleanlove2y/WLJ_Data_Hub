# 增量同步功能使用指南

## 功能概述

增量同步功能允许您只更新指定的表，而不是重新扫描整个数据库，从而大幅减少数据库查询压力。系统会自动识别目标数据库并将更新合并到正确的文件中。

## 核心优势

- **极低数据库压力**：只查询指定的表，而不是全库扫描
- **使用便捷**：通过文件管理需要更新的表列表
- **智能合并**：新数据会与现有文档合并（支持interactive-html格式）
- **自动识别**：根据配置文件自动识别目标数据库和文件
- **安全检查**：验证数据库匹配，防止更新错误的文件
- **团队协作**：增量表文件可以版本控制

## 使用方法

### 1. 基本使用（推荐）

```bash
# 1. 编辑增量表文件
vim incremental_tables.txt

# 2. 添加需要更新的表名
user_info
order_detail
product_catalog

# 3. 运行增量同步
python generate_data_dictionary.py --incremental
```

### 2. 命令行直接指定表

```bash
# 直接在命令行指定表（会覆盖文件中的设置）
python generate_data_dictionary.py --incremental --tables user_info,order_detail
```

### 3. 使用自定义文件

```bash
# 使用自定义的增量表文件
python generate_data_dictionary.py --incremental --tables-file my_changes.txt
```

### 4. 管理增量表文件

```bash
# 查看当前增量表文件内容
python generate_data_dictionary.py --show-incremental-file

# 清空增量表文件
python generate_data_dictionary.py --clear-incremental-file

# 查看自定义文件内容
python generate_data_dictionary.py --show-incremental-file --tables-file my_changes.txt
```

### 5. 查看增量同步状态

```bash
# 检查增量同步状态（数据库匹配、目标文件等）
python generate_data_dictionary.py --show-incremental-status

# 使用特定配置文件检查状态
python generate_data_dictionary.py --show-incremental-status --config prod_config.ini

# 使用特定环境检查状态
python generate_data_dictionary.py --show-incremental-status --env production
```

## 增量表文件格式

`incremental_tables.txt` 文件格式：

```txt
# 增量更新表列表
# 格式：每行一个表名，# 开头为注释

# 用户相关表
user_info
user_profile
user_settings

# 订单相关表  
order_detail
order_payment

# 产品相关表
product_catalog
```

## 工作流程

1. **开发阶段**：修改数据库表结构
2. **记录变更**：将变更的表名添加到 `incremental_tables.txt`
3. **运行同步**：`python generate_data_dictionary.py --incremental`
4. **自动合并**：脚本自动将新数据合并到现有文档
5. **清理文件**：同步完成后可以清空增量表文件

## 数据库压力对比

### 全量同步（1000个表的场景）
- 查询次数：约2001次
- 查询内容：所有表的结构信息

### 增量同步（10个表的场景）
- 查询次数：约31次
- 查询内容：只查询指定的表
- **压力降低：98.5%**

## 支持的输出格式

### 完全支持（智能合并）
- `interactive-html`：完美支持，新数据会合并到现有HTML文件中

### 部分支持（覆盖模式）
- `markdown`、`excel`、`csv`、`html`：会覆盖现有文件

## 状态管理

增量同步会自动保存状态信息到 `{output_filename}_incremental_state.json`：

```json
{
  "last_sync": "2024-01-16T14:20:00",
  "database": {
    "name": "my_database",
    "host": "localhost",
    "port": "3306",
    "user": "db_user"
  },
  "tables_count": 150,
  "tables": ["user_info", "order_detail", "..."],
  "updated_tables": ["user_info", "order_detail"]
}
```

您可以随时检查增量同步状态：

```bash
python generate_data_dictionary.py --show-incremental-status
```

这将显示：
- 当前配置的数据库信息
- 上次同步的时间和表数量
- 数据库配置是否匹配
- 目标HTML文件是否存在和匹配

## 最佳实践

### 1. 推荐的工作流程
```bash
# 开发完成后，记录变更的表
echo "user_info" >> incremental_tables.txt
echo "order_detail" >> incremental_tables.txt

# 运行增量同步
python generate_data_dictionary.py --incremental --output-format interactive-html

# 清空增量表文件，准备下次使用
python generate_data_dictionary.py --clear-incremental-file
```

### 2. 团队协作
- 将 `incremental_tables.txt` 加入版本控制
- 团队成员可以共同维护需要更新的表列表
- 定期运行增量同步保持文档最新

### 3. 定期全量同步
```bash
# 每周或每月运行一次全量同步，确保数据完整性
python generate_data_dictionary.py --output-format interactive-html
```

## 注意事项

1. **首次使用**：如果没有现有的数据字典文件，会自动创建新文件
2. **格式限制**：智能合并目前只支持 `interactive-html` 格式
3. **表名准确性**：确保增量表文件中的表名在数据库中存在
4. **数据库匹配**：系统会验证目标HTML文件是否属于当前数据库
5. **配置变更**：如果数据库配置发生变化，请检查增量同步状态
6. **备份建议**：重要的数据字典文件建议定期备份

## 故障排除

### 问题1：增量表文件为空
```bash
# 检查文件内容
python generate_data_dictionary.py --show-incremental-file

# 添加示例内容
python generate_data_dictionary.py --clear-incremental-file
```

### 问题2：表名不存在
- 检查表名拼写是否正确
- 确认表在当前数据库中存在
- 查看脚本输出的错误信息

### 问题3：合并失败
- 检查现有HTML文件是否损坏
- 尝试重新生成完整的数据字典
- 查看错误日志信息

### 问题4：数据库不匹配
```bash
# 检查增量同步状态
python generate_data_dictionary.py --show-incremental-status

# 如果数据库不匹配，可以:
# 1. 确认使用了正确的配置文件
# 2. 使用不同的输出文件名
python generate_data_dictionary.py --incremental --output-file new_database_docs
```

## 示例场景

### 场景1：新增用户表
```bash
# 1. 添加到增量文件
echo "user_new_table" >> incremental_tables.txt

# 2. 运行增量同步
python generate_data_dictionary.py --incremental

# 3. 清理
python generate_data_dictionary.py --clear-incremental-file
```

### 场景2：批量更新订单相关表
```bash
# 1. 批量添加
cat >> incremental_tables.txt << EOF
order_main
order_detail
order_payment
order_shipping
EOF

# 2. 运行同步
python generate_data_dictionary.py --incremental

# 3. 清理
python generate_data_dictionary.py --clear-incremental-file
```

通过增量同步功能，您可以高效地维护数据字典，同时最大化减少对数据库的压力！