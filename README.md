# 数据字典生成工具

这个工具可以从各种数据库中提取表结构信息，并生成易于浏览的数据字典文档。

## 功能特点

- 支持多种数据库：SQL Server、MySQL、PostgreSQL、Oracle
- 支持多种输出格式：Markdown、Excel、HTML、交互式HTML、CSV
- 交互式HTML格式提供搜索功能，方便快速查找表和字段
- 支持表过滤，可以只生成指定表的数据字典
- 支持多数据库环境配置管理

## 安装依赖

```bash
pip install -r requirements.txt
```

## 基本用法

```bash
# 使用默认配置
python generate_data_dictionary.py

# 指定输出格式
python generate_data_dictionary.py --output-format interactive-html

# 测试数据库连接
python generate_data_dictionary.py --test-connection

# 只包含特定表
python generate_data_dictionary.py --include-tables table1,table2,table3

# 排除特定表
python generate_data_dictionary.py --exclude-tables log_,tmp_
```

## 工作流程

以下是数据字典生成脚本的工作流程图：

```mermaid
graph TD
    A[开始] --> B(用户运行脚本);
    B --> C{指定配置文件和环境?};
    C -- 是 --> D[读取指定配置文件和环境];
    C -- 否 --> E[读取默认配置文件];
    D --> F{多环境配置?};
    E --> F;
    F -- 是 --> G[解析多环境配置];
    F -- 否 --> H[解析单环境配置];
    G --> I[获取数据库连接信息];
    H --> I;
    I --> J[连接数据库];
    J --> K[提取Schema信息];
    K --> L[根据输出格式生成数据字典];
    L --> M[输出文件];
    M --> N[结束];
```

## 配置文件

工具使用`config.ini`文件进行配置，示例如下：

```ini
[database]
type = sqlserver
host = localhost
port = 1433
database = my_database
user = username
password = password
driver = SQL Server

[output]
format = interactive-html
filename = 
```

## 多数据库环境管理

工具支持两种方式管理多个数据库环境：使用多个配置文件或在单个配置文件中定义多个环境。这两种方式都支持不同类型的数据库（SQL Server、MySQL、PostgreSQL、Oracle）。

### 方案1：多配置文件

为每个数据库环境创建单独的配置文件，适合管理不同类型的数据库：

```bash
# 使用SQL Server数据库配置
python generate_data_dictionary.py --config config_sqlserver.ini

# 使用PostgreSQL数据库配置
python generate_data_dictionary.py --config config_pgsql.ini
```

配置文件示例（SQL Server）：
```ini
[database]
type = sqlserver
host = localhost
port = 1433
database = my_sqlserver_db
user = sqlserver_user
password = password123
driver = SQL Server

[output]
format = interactive-html
filename = 
```

配置文件示例（PostgreSQL）：
```ini
[database]
type = postgresql
host = 192.168.1.100
port = 5432
database = my_pgsql_db
user = pgsql_user
password = password456

[output]
format = interactive-html
filename = 
```

### 方案2：多环境配置文件

使用`multi_db_support.py`模块，在单个配置文件中定义多个环境，可以包含不同类型的数据库：

```bash
# 查看所有可用环境
python generate_data_dictionary.py --config config_multi_env.ini --list-env

# 使用指定环境生成数据字典
python generate_data_dictionary.py --config config_multi_env.ini --env sqlserver
```

多环境配置文件示例（包含不同类型的数据库）：

```ini
[environment]
default = sqlserver

[database:sqlserver]
type = sqlserver
host = localhost
port = 1433
database = my_sqlserver_db
user = sqlserver_user
password = password123
driver = SQL Server

[database:postgresql]
type = postgresql
host = 192.168.1.100
port = 5432
database = my_pgsql_db
user = pgsql_user
password = password456

[output]
format = interactive-html
filename = 
```

## 输出格式说明

- **markdown**: 生成单个Markdown文件
- **excel**: 生成Excel文件，每个表一个工作表
- **html**: 生成HTML文件，适合在浏览器中查看
- **interactive-html**: 生成交互式HTML文件，带有搜索功能（推荐）
- **csv**: 生成CSV文件

## 注意事项

- 对于大型数据库（表数量超过100个），建议使用interactive-html格式
- 所有输出文件会放在以数据库信息命名的文件夹中，方便管理
- 密码信息存储在配置文件中，请确保配置文件的安全性
