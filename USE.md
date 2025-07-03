## 常用指令示例

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