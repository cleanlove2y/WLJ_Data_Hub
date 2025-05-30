# AI 提示词：自动化数据库注释提取与数据字典生成

## 任务概述

我需要一个 Python 脚本，能够自动化从数据库中提取表和字段的注释，并将这些注释格式化成易于阅读的数据字典文件。这个数据字典应该包含数据库中的所有表及其对应的字段信息，包括字段名、数据类型、是否可空、默认值以及最重要的注释。

## 核心功能需求

1.  **数据库连接**：
    *   支持多种主流关系型数据库（例如：MySQL, PostgreSQL, SQL Server, Oracle）。
    *   能够通过配置文件（例如：`config.ini` 或 `settings.py`）管理数据库连接信息，包括主机、端口、数据库名、用户名和密码。

2.  **注释提取**：
    *   能够查询指定数据库中的所有表名。
    *   对于每个表，能够查询其所有字段的详细信息，包括：
        *   字段名 (Column Name)
        *   数据类型 (Data Type)
        *   是否可空 (Is Nullable)
        *   默认值 (Default Value)
        *   **注释 (Comment/Description)**：这是最核心的信息。
    *   需要考虑不同数据库系统获取注释的方式可能不同（例如：MySQL 的 `INFORMATION_SCHEMA`，PostgreSQL 的 `pg_description` 和 `information_schema`，SQL Server 的 `sys.extended_properties`）。

3.  **数据字典格式化输出**：
    *   支持多种输出格式，例如：
        *   Markdown (`.md`)：易于阅读和版本控制。
        *   Excel (`.xlsx`)：方便非技术人员查看和筛选。
        *   CSV (`.csv`)：便于进一步处理。
    *   输出文件应结构清晰，每个表为一个独立的章节或工作表，包含所有字段的详细信息。
    *   Markdown 格式示例：

        ```markdown
        # 数据库名：[YourDatabaseName]

        ## 表名：users

        | 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
        |---|---|---|---|---|
        | id | INT | NO | NULL | 用户唯一标识 |
        | username | VARCHAR(50) | NO | NULL | 用户名 |
        | email | VARCHAR(100) | YES | NULL | 用户邮箱 |
        | created_at | DATETIME | NO | CURRENT_TIMESTAMP | 记录创建时间 |

        ## 表名：products

        | 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
        |---|---|---|---|---|
        | id | INT | NO | NULL | 产品唯一标识 |
        | name | VARCHAR(255) | NO | NULL | 产品名称 |
        | description | TEXT | YES | NULL | 产品描述 |
        | price | DECIMAL(10, 2) | NO | 0.00 | 产品价格 |
        ```

4.  **错误处理与日志**：
    *   健壮的错误处理机制，例如数据库连接失败、查询失败等。
    *   记录操作日志，方便调试和问题追踪。

## 技术栈建议

*   **Python 版本**：Python 3.x
*   **数据库连接库**：
    *   `SQLAlchemy`：提供统一的 ORM 和 SQL Expression Language，方便支持多种数据库。
    *   或者针对特定数据库使用原生驱动（例如：`pymysql`, `psycopg2`, `pyodbc`）。
*   **数据处理**：`pandas` (用于 Excel/CSV 输出)
*   **配置文件解析**：`configparser` 或 `PyYAML`

## 交付物

*   一个 Python 脚本文件（例如：`generate_data_dictionary.py`）。
*   一个配置文件示例（例如：`config.ini.example`）。
*   一个 `requirements.txt` 文件，列出所有依赖。
*   （可选）一个简单的 `README.md`，说明如何运行和配置脚本。

## 额外考虑

*   **命令行参数**：是否可以通过命令行参数指定数据库类型、配置文件路径、输出格式和输出文件路径。
*   **过滤机制**：是否支持只提取特定表或排除某些表。
*   **安全性**：数据库密码等敏感信息如何安全处理（例如：环境变量、加密）。

请根据以上需求，帮助我生成一个完整的 Python 脚本和相关文件。
