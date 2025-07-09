# 增量同步功能使用示例

## 快速开始

### 1. 查看增量表文件
```bash
# 查看默认增量表文件内容
python generate_data_dictionary.py --show-incremental-file

# 查看自定义文件内容
python generate_data_dictionary.py --show-incremental-file --tables-file my_tables.txt
```

### 1.5. 检查增量同步状态
```bash
# 检查当前增量同步状态（数据库匹配、目标文件等）
python generate_data_dictionary.py --show-incremental-status

# 使用特定配置文件检查状态
python generate_data_dictionary.py --show-incremental-status --config prod_config.ini
```

### 2. 编辑增量表文件
编辑 `incremental_tables.txt` 文件，添加需要更新的表：
```txt
# 增量更新表列表
user_info
order_detail
product_catalog
```

### 3. 运行增量同步
```bash
# 使用默认文件进行增量同步
python generate_data_dictionary.py --incremental --output-format interactive-html

# 使用命令行直接指定表
python generate_data_dictionary.py --incremental --tables user_info,order_detail --output-format interactive-html
```

## 完整工作流程示例

### 场景：更新用户相关的表

1. **添加表到增量文件**
```bash
# 方法1：直接编辑文件
echo "user_info" >> incremental_tables.txt
echo "user_profile" >> incremental_tables.txt
echo "user_settings" >> incremental_tables.txt

# 方法2：批量添加
cat >> incremental_tables.txt << EOF
user_info
user_profile
user_settings
EOF
```

2. **查看文件内容确认**
```bash
python generate_data_dictionary.py --show-incremental-file
```

3. **运行增量同步**
```bash
python generate_data_dictionary.py --incremental --output-format interactive-html
```

4. **清空文件准备下次使用**
```bash
python generate_data_dictionary.py --clear-incremental-file
```

## 高级使用示例

### 1. 结合配置文件使用
```bash
# 使用特定环境的配置进行增量同步
python generate_data_dictionary.py --incremental --env production --output-format interactive-html
```

### 2. 自定义输出文件名
```bash
# 指定输出文件名
python generate_data_dictionary.py --incremental --output-file my_database_docs --output-format interactive-html
```

### 3. 使用自定义增量文件
```bash
# 创建专门的增量文件
echo "order_main" > order_tables.txt
echo "order_detail" >> order_tables.txt
echo "order_payment" >> order_tables.txt

# 使用自定义文件
python generate_data_dictionary.py --incremental --tables-file order_tables.txt --output-format interactive-html
```

## 数据库压力对比测试

### 全量同步（示例：1000个表）
```bash
# 全量同步 - 高数据库压力
time python generate_data_dictionary.py --output-format interactive-html
# 预期：约2001次数据库查询，耗时较长
```

### 增量同步（示例：10个表）
```bash
# 增量同步 - 低数据库压力
echo -e "user_info\norder_detail\nproduct_catalog" > incremental_tables.txt
time python generate_data_dictionary.py --incremental --output-format interactive-html
# 预期：约31次数据库查询，耗时大幅减少
```

## 错误处理示例

### 1. 增量文件为空
```bash
# 清空文件
python generate_data_dictionary.py --clear-incremental-file

# 尝试运行增量同步（会报错）
python generate_data_dictionary.py --incremental
# 输出：错误: 增量同步模式下没有指定要更新的表
```

### 2. 表名不存在
```bash
# 添加不存在的表名
echo "non_existent_table" > incremental_tables.txt

# 运行增量同步
python generate_data_dictionary.py --incremental --output-format interactive-html
# 脚本会跳过不存在的表并继续处理其他表
```

### 3. 数据库不匹配
```bash
# 检查增量同步状态
python generate_data_dictionary.py --show-incremental-status

# 如果显示数据库不匹配，可以:
# 1. 确认使用了正确的配置文件
python generate_data_dictionary.py --incremental --config correct_config.ini

# 2. 使用特定环境
python generate_data_dictionary.py --incremental --env production

# 3. 使用不同的输出文件名
python generate_data_dictionary.py --incremental --output-file new_database_docs
```

## 团队协作示例

### 1. 版本控制集成
```bash
# 将增量文件加入版本控制
git add incremental_tables.txt
git commit -m "Add tables for incremental sync"

# 团队成员拉取更新
git pull

# 运行增量同步
python generate_data_dictionary.py --incremental --output-format interactive-html
```

### 2. CI/CD 集成
```yaml
# .github/workflows/docs.yml
name: Update Data Dictionary
on:
  push:
    paths:
      - 'incremental_tables.txt'
      - 'migrations/**'

jobs:
  update-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run incremental sync
        run: python generate_data_dictionary.py --incremental --output-format interactive-html
      - name: Deploy docs
        run: # 部署到文档服务器
```

## 性能优化建议

### 1. 定期全量同步
```bash
# 每周运行一次全量同步确保数据完整性
# 0 2 * * 0 /path/to/python /path/to/generate_data_dictionary.py --output-format interactive-html

# 日常使用增量同步
python generate_data_dictionary.py --incremental --output-format interactive-html
```

### 2. 批量处理
```bash
# 收集一天的所有变更，批量处理
cat >> daily_changes.txt << EOF
user_info
order_detail
product_catalog
payment_log
EOF

# 一次性处理所有变更
python generate_data_dictionary.py --incremental --tables-file daily_changes.txt --output-format interactive-html

# 清理
rm daily_changes.txt
```

## 监控和日志

### 1. 记录增量同步历史
```bash
# 查看增量同步状态文件
cat *_incremental_state.json

# 示例输出：
# {
#   "last_sync": "2024-01-16T14:20:00",
#   "database": {
#     "name": "my_database",
#     "host": "localhost",
#     "port": "3306",
#     "user": "db_user"
#   },
#   "tables_count": 150,
#   "tables": ["user_info", "order_detail", "..."],
#   "updated_tables": ["user_info", "order_detail"]
# }

# 使用内置命令查看状态（推荐）
python generate_data_dictionary.py --show-incremental-status
```

### 2. 自动化脚本示例
```bash
#!/bin/bash
# auto_incremental_sync.sh

LOG_FILE="incremental_sync.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting incremental sync..." >> $LOG_FILE

if python generate_data_dictionary.py --incremental --output-format interactive-html; then
    echo "[$DATE] Incremental sync completed successfully" >> $LOG_FILE
    python generate_data_dictionary.py --clear-incremental-file
    echo "[$DATE] Cleared incremental tables file" >> $LOG_FILE
else
    echo "[$DATE] Incremental sync failed" >> $LOG_FILE
    exit 1
fi
```

通过这些示例，您可以充分利用增量同步功能，大幅减少数据库压力，提高数据字典维护效率！