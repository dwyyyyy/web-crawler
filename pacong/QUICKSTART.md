# ⚡ 快速开始

## 🚀 运行系统（3步）

```bash
pip install -r requirements.txt
python main.py
ls reports/
```

## 📝 添加新网站

编辑 `config/settings.yaml`：

```yaml
simple_scrapers:
  my_site:
    enabled: true
    name: "新网站"
    urls: "https://example.com/api"
    method: "requests"
```

## 🔧 常用命令

```bash
python main.py --list-scrapers        # 查看数据源
python main.py --scrapers sina_forex_futures # 运行特定源  
python main.py --log-level DEBUG      # 调试模式
```

## 📊 输出结果

- 📄 CSV: `reports/commodity_data_*.csv`
- 📈 Excel: `reports/commodity_data_*.xlsx`

---

**需要帮助？** 查看 [README.md](README.md) 