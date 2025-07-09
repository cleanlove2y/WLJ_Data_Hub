# 数据字典生成器 - 搜索功能使用指南

## 搜索功能说明

本工具的搜索功能**仅限于**通过 `interactive-html` 格式生成的HTML页面。在命令行（`generate_data_dictionary.py`）中，**不提供** `--search-keyword` 或 `--search-mode` 等参数来过滤表。

## 如何使用搜索功能

1.  生成交互式HTML格式的数据字典：
    ```bash
    python generate_data_dictionary.py --output-format interactive-html
    ```

2.  在浏览器中打开生成的HTML文件。

3.  使用页面顶部的搜索框进行实时搜索。功能包括：
    - **实时筛选**：输入关键词，表单列表会即时更新。
    - **内容高亮**：匹配的关键词会在表格内容中高亮显示。
    - **多维度搜索**：可以搜索表名、字段名、数据类型、注释等所有可见内容。

## 推荐使用场景

当数据库中的表数量非常多时，生成一份完整的 `interactive-html` 文档，然后利用其强大的前端搜索功能，可以快速、精确地定位到您需要的表信息，极大提高查阅效率。