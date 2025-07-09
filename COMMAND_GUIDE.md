# `generate_data_dictionary.py` 指令使用指南

本文档旨在详细说明 `generate_data_dictionary.py` 脚本的各种指令和参数，帮助您在不同场景下高效地使用该脚本。

## 常用指令示例

### `--list-env`

- **作用**：列出多环境配置文件中所有可用的环境名称并退出。
- **示例**：
```bash
python generate_data_dictionary.py --config config_multi_env.ini --list-env
```

### 1. 生成生产环境（sqlserver-prod）的完整数据字典

```bash
python generate_data_dictionary.py --config config_multi_env.ini --env sqlserver-prod
```

### 2. 对生产环境（sqlserver-prod）进行增量更新

此操作会读取 `incremental_tables.txt` 文件，只更新其中列出的表。

```bash
python generate_data_dictionary.py --config config_multi_env.ini --env sqlserver-prod --incremental
```

### 3. 对生产环境（sqlserver-prod）查看增量更新状况

```bash
python generate_data_dictionary.py --config config_multi_env.ini --env sqlserver-prod --show-incremental-status
```

## 1. 基本用法

最基础的用法是指定配置文件和输出格式，生成一个完整的数据字典。

```bash
python generate_data_dictionary.py --config config.ini --format interactive-html
```

## 2. 核心功能参数

这些参数用于控制数据库连接和要处理的表范围。

### `--config <file_path>`

- **作用**：指定配置文件的路径。
- **默认值**：`config.ini`
- **示例**：使用一个名为 `prod_config.ini` 的配置文件。
```bash
python generate_data_dictionary.py --config prod_config.ini
```

### `--env <environment_name>`

- **作用**：当使用多环境配置文件 (如 `config_multi_env.ini`) 时，指定要使用的数据库环境。
- **示例**：使用 `development` 环境的配置。
```bash
python generate_data_dictionary.py --config config_multi_env.ini --env development
```

### `--include-tables <table1,table2,...>`

- **作用**：只为指定的表生成数据字典，多个表名用逗号隔开。
- **示例**：只处理 `users` 和 `orders` 表。
```bash
python generate_data_dictionary.py --include-tables users,orders
```

### `--exclude-tables <table1,table2,...>`

- **作用**：从所有表中排除指定的表，多个表名用逗号隔开。
- **示例**：处理除 `logs` 和 `temp_data` 之外的所有表。
```bash
python generate_data_dictionary.py --exclude-tables logs,temp_data
```

## 3. 输出格式参数

### `--format <format_type>`

- **作用**：指定生成数据字典的格式。
- **默认值**：`interactive-html`
- **可选值**：
  - `interactive-html`: (推荐) 生成一个功能强大的、带实时搜索和过滤的单页HTML应用。
  - `html`: 生成静态的HTML文件，如果表太多会分页。
  - `excel`: 生成Excel文件，每个表是一个Sheet。如果表太多会分文件。
  - `markdown`: 生成Markdown格式的文件。
  - `csv`: 为每个表生成一个单独的CSV文件。
- **示例**：生成Excel格式的数据字典。
```bash
python generate_data_dictionary.py --format excel
```

### `--output <filename_base>`

- **作用**：指定输出文件或文件夹的基础名称 (不含扩展名)。
- **默认值**：`{db_name}_data_dictionary`
- **示例**：将输出文件命名为 `my_project_dict`。
```bash
python generate_data_dictionary.py --output my_project_dict
```

## 4. 搜索与过滤参数

当您只想查找数据库中特定的内容时，这些参数非常有用。

### `--search <keyword>`

- **作用**：根据关键词进行搜索，只输出匹配的表。
- **示例**：搜索所有与“user”相关的表。
```bash
python generate_data_dictionary.py --search user
```

### `--search-mode <mode>`

- **作用**：与 `--search` 配合使用，定义搜索范围，使搜索更精确。
- **默认值**：`all`
- **可选值**：
  - `all`: 搜索所有地方 (表名, 字段名, 表注释, 字段注释)。
  - `table_name`: 只搜索表名。
  - `column_name`: 只搜索字段名。
  - `comment`: 搜索表注释和字段注释。
  - `table_comment`: 只搜索表注释。
  - `column_comment`: 只搜索字段注释。
- **示例**：只在字段注释中搜索包含“订单ID”的表。
```bash
python generate_data_dictionary.py --search "订单ID" --search-mode column_comment
```

## 5. 增量同步参数

增量同步功能非常适合大型数据库，当您只想更新少数几个表的文档时，可以避免全量扫描，极大地提高效率。它主要配合 `interactive-html` 格式使用。

### `--incremental`

- **作用**：启用增量同步模式。脚本会合并新旧数据，而不是完全重写。
- **用法**：此参数需要配合 `--tables` 或 `--tables-file` 使用。
- **示例**：增量更新 `users` 表到现有的数据字典中。
```bash
python generate_data_dictionary.py --incremental --tables users
```

### `--tables <table1,table2,...>`

- **作用**：在增量模式下，直接从命令行指定要更新的表。
- **示例**：同上。

### `--tables-file <file_path>`

- **作用**：在增量模式下，从一个文件读取要更新的表列表 (每行一个表名)。
- **默认值**：`incremental_tables.txt`
- **示例**：
  1. 编辑 `incremental_tables.txt` 文件，添加 `products` 和 `categories`。
  2. 运行以下指令：
```bash
python generate_data_dictionary.py --incremental --tables-file incremental_tables.txt
```

### `--show-incremental-status`

- **作用**：显示当前增量同步的状态，包括上次同步时间、数据库信息、目标文件状态等。
- **示例**：
```bash
python generate_data_dictionary.py --show-incremental-status
```

### `--show-incremental-file`

- **作用**：显示增量表文件 (`incremental_tables.txt`) 的内容。
- **示例**：
```bash
python generate_data_dictionary.py --show-incremental-file
```

### `--clear-incremental-file`

- **作用**：清空增量表文件 (`incremental_tables.txt`) 的内容。
- **示例**：
```bash
python generate_data_dictionary.py --clear-incremental-file
```

## 6. 辅助指令

这些指令不生成数据字典，而是提供一些有用的辅助功能。

### `--list-env`

- **作用**：列出多环境配置文件中所有可用的环境名称并退出。
- **示例**：
```bash
python generate_data_dictionary.py --config config_multi_env.ini --list-env
```

### `--test-connection`

- **作用**：测试数据库连接是否成功并退出。
- **示例**：
```bash
python generate_data_dictionary.py --test-connection
```
