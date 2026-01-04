# 多源新闻感知与整合系统

基于LangGraph的深思熟虑型智能体架构，实现一个多源新闻感知与整合系统。系统能够依次访问多个新闻网站首页，感知每个网站的最新新闻和信息，构建内部世界模型，理解内容并转换为中文，最后整合所有信息生成综合新闻报告。

## 功能特性

- ✅ 支持多种网站类型（财经、科技、综合新闻、论坛）
- ✅ 自动缓存网页内容，避免重复抓取
- ✅ 多语言支持，自动转换为中文
- ✅ 支持串行和并行处理
- ✅ 完整的错误处理和容错机制
- ✅ 生成结构化的综合新闻报告

## 项目结构

```
news_ai_research/
├── website_perceptor.py      # 网站感知器基类和具体实现
├── news_manager.py           # 网站感知器管理器
├── news_integration.py       # 新闻整合智能体
├── main.py                   # 主程序入口
├── website_config.json        # 网站配置文件
├── requirements.txt          # 依赖项
├── implementation_framework.md # 实现框架文档
├── cache/                    # 缓存目录（自动创建）
└── README.md                 # 本文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 1. 配置文件 `website_config.json`

配置文件包含三个主要部分：

- **websites**: 网站列表，每个网站包含：
  - `name`: 网站名称
  - `url`: 网站URL
  - `type`: 网站类型（financial/tech/general/forum）
  - `model`: 使用的模型（Qwen-Turbo/Qwen-Max）
  - `language`: 网站主要语言（en/zh/auto）
  - `description`: 网站描述

- **api_keys**: API密钥配置
  - `dashscope`: 通义千问API密钥

- **settings**: 系统设置
  - `parallel_processing`: 是否并行处理（默认：false）
  - `cache_enabled`: 是否启用缓存（默认：true）
  - `cache_max_age_hours`: 缓存有效期（小时，默认：24）
  - `cache_dir`: 缓存目录（默认：cache）
  - `force_refresh`: 强制刷新缓存（默认：false）

### 2. 配置API密钥

在 `website_config.json` 中设置你的通义千问API密钥：

```json
{
  "api_keys": {
    "dashscope": "your-api-key-here"
  }
}
```

## 使用方法

### 基本使用

```bash
python main.py
```

程序会：
1. 加载配置文件
2. 初始化所有网站感知器
3. 依次处理每个网站（使用缓存或抓取新内容）
4. 整合所有内容生成综合报告
5. 保存报告到文件

### 缓存机制

- 首次运行会抓取所有网站内容并保存到 `cache/` 目录
- 后续运行会优先使用缓存内容（24小时内有效）
- 可以通过设置 `force_refresh: true` 强制刷新缓存

### 并行处理

在配置文件中设置 `parallel_processing: true` 可以启用并行处理，提高处理速度。

## 输出说明

### 缓存文件

所有网页内容备份存储在 `cache/` 目录下，文件命名格式：
```
{网站名称}_{URL的MD5哈希值}.html
```

### 报告文件

生成的综合新闻报告保存为Markdown格式，文件名格式：
```
news_report_{时间戳}.md
```

报告包含：
- 报告标题和摘要
- 主要新闻事件（按重要性排序）
- 共同主题和趋势分析
- 不同来源的视角对比
- 关键发现和洞察
- 结论和建议

## 网站类型说明

### FinancialNewsPerceptor（财经新闻感知器）
- 适用于：Bloomberg、Financial Times、雪球、经济时报等
- 特点：关注财经指标、市场动态、股票、汇率、经济数据

### TechNewsPerceptor（科技新闻感知器）
- 适用于：Medium、齐思、科技类网站
- 特点：关注技术趋势、产品发布、AI、机器学习相关新闻

### GeneralNewsPerceptor（综合新闻感知器）
- 适用于：新华网、人民网、南华早报等
- 特点：关注综合新闻、社会动态、政治、经济、社会新闻

### ForumPerceptor（论坛感知器）
- 适用于：Reddit、Discuss.com.hk、Mobile01等
- 特点：关注热门话题、讨论趋势、用户观点、热点话题

## 注意事项

1. **API限制**：注意大模型API的调用频率和配额限制
2. **网页抓取**：遵守网站的robots.txt和使用条款
3. **内容版权**：注意内容的版权问题，仅用于研究目的
4. **网络稳定性**：处理网络不稳定和网站访问限制的情况
5. **缓存管理**：定期清理缓存，避免占用过多磁盘空间

## 故障排除

### 网页抓取失败
- 检查网络连接
- 确认网站URL是否正确
- 某些网站可能需要特殊处理（JavaScript渲染等）

### API调用失败
- 检查API密钥是否正确
- 确认API配额是否充足
- 检查网络连接

### 缓存问题
- 可以删除 `cache/` 目录强制重新抓取
- 检查缓存目录权限

## 扩展开发

### 添加新网站

在 `website_config.json` 中添加网站配置：

```json
{
  "name": "新网站",
  "url": "https://example.com/",
  "type": "general",
  "model": "Qwen-Turbo",
  "language": "zh",
  "description": "网站描述"
}
```

### 自定义感知器

继承 `WebsitePerceptorBase` 并实现自定义的 `perception` 方法：

```python
class CustomPerceptor(WebsitePerceptorBase):
    def perception(self, content: str) -> Dict[str, Any]:
        # 自定义感知逻辑
        pass
```

## 许可证

本项目仅供学习和研究使用。

