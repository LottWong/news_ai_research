# 多源新闻感知与整合系统 - 实现思路与框架设计

## 一、项目概述

基于LangGraph的深思熟虑型智能体架构，实现一个多源新闻感知与整合系统。系统能够：
1. 依次访问多个新闻网站首页
2. 感知每个网站的最新新闻和信息
3. 构建内部世界模型，理解内容并转换为中文
4. 整合所有信息，生成最终的综合新闻报告

## 二、整体架构设计

### 2.1 架构层次

```
┌─────────────────────────────────────────────────────────┐
│              整合与报告生成层 (Integration Layer)        │
│  - 整合所有网站的中文内容                                │
│  - 生成最终综合新闻报告                                  │
└─────────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────────┐
│           网站感知器管理层 (Manager Layer)               │
│  - 管理多个网站感知器实例                                │
│  - 协调并行/串行处理                                     │
│  - 收集各网站处理结果                                    │
└─────────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────────┐
│           网站感知器层 (Perceptor Layer)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ 财经网站 │  │ 科技网站 │  │ 新闻网站 │  ...         │
│  │感知器实例│  │感知器实例│  │感知器实例│             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────────┐
│           数据获取层 (Data Acquisition Layer)            │
│  - 网页内容抓取                                         │
│  - 内容清洗和预处理                                      │
│  - 缓存管理（存储到cache文件夹）                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心流程

```
开始
  ↓
初始化所有网站感知器
  ↓
┌─────────────────────┐
│ 对每个网站感知器：   │
│ 1. 获取网页内容      │
│ 2. 感知阶段          │
│ 3. 建模阶段          │
│ 4. 输出中文内容      │
└─────────────────────┘
  ↓
收集所有中文内容
  ↓
整合与思考阶段
  ↓
生成最终报告
  ↓
结束
```

## 三、类设计

### 3.1 基类设计

#### 3.1.1 WebsitePerceptorBase（网站感知器基类）

```python
class WebsitePerceptorBase:
    """网站感知器基类"""
    
    def __init__(
        self,
        url: str,
        name: str,
        model_name: str,
        api_key: str,
        language: str = "auto",  # 网站主要语言
        description: str = ""
    ):
        self.url = url
        self.name = name
        self.model_name = model_name
        self.api_key = api_key
        self.language = language
        self.description = description
        self.llm = None  # LLM实例
        
    def get_cache_path(self) -> str:
        """获取缓存文件路径"""
        import hashlib
        import os
        from urllib.parse import urlparse
        
        # 使用URL的hash值作为文件名
        url_hash = hashlib.md5(self.url.encode()).hexdigest()
        cache_dir = "cache"
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{self.name}_{url_hash}.html")
    
    def load_from_cache(self, cache_path: str, max_age_hours: int = 24) -> Optional[str]:
        """从缓存加载内容"""
        import os
        from datetime import datetime, timedelta
        
        if not os.path.exists(cache_path):
            return None
        
        # 检查缓存是否过期
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - file_time > timedelta(hours=max_age_hours):
            return None
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def save_to_cache(self, content: str, cache_path: str):
        """保存内容到缓存"""
        import os
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def fetch_content(self, use_cache: bool = True, max_cache_age_hours: int = 24) -> str:
        """获取网页内容（子类实现）
        
        Args:
            use_cache: 是否使用缓存
            max_cache_age_hours: 缓存最大有效期（小时）
        """
        raise NotImplementedError
        
    def perception(self, content: str) -> Dict[str, Any]:
        """感知阶段：提取新闻和信息"""
        raise NotImplementedError
        
    def modeling(self, perception_data: Dict[str, Any]) -> Dict[str, Any]:
        """建模阶段：构建内部世界模型"""
        raise NotImplementedError
        
    def translate_to_chinese(self, world_model: Dict[str, Any]) -> Dict[str, Any]:
        """将世界模型转换为中文"""
        raise NotImplementedError
        
    def process(self) -> Dict[str, Any]:
        """完整处理流程"""
        # 1. 获取内容
        # 2. 感知
        # 3. 建模
        # 4. 转换为中文
        # 5. 返回结果
        pass
```

### 3.2 具体实现类

#### 3.2.1 FinancialNewsPerceptor（财经新闻感知器）

适用于：Bloomberg、Financial Times、雪球、经济时报等

特点：
- 关注财经指标、市场动态
- 提取股票、汇率、经济数据
- 使用适合财经分析的模型

#### 3.2.2 TechNewsPerceptor（科技新闻感知器）

适用于：Medium、齐思、科技类网站

特点：
- 关注技术趋势、产品发布
- 提取AI、机器学习相关新闻
- 使用适合技术分析的模型

#### 3.2.3 GeneralNewsPerceptor（综合新闻感知器）

适用于：新华网、人民网、南华早报等

特点：
- 关注综合新闻、社会动态
- 提取政治、经济、社会新闻
- 使用通用模型

#### 3.2.4 ForumPerceptor（论坛感知器）

适用于：Reddit、Discuss.com.hk、Mobile01等

特点：
- 关注热门话题、讨论趋势
- 提取用户观点、热点话题
- 需要特殊的内容提取策略

### 3.3 管理器类

#### 3.3.1 WebsitePerceptorManager（网站感知器管理器）

```python
class WebsitePerceptorManager:
    """管理多个网站感知器"""
    
    def __init__(self):
        self.perceptors = []
        
    def add_perceptor(self, perceptor: WebsitePerceptorBase):
        """添加感知器"""
        pass
        
    def process_all(self, parallel: bool = False) -> List[Dict[str, Any]]:
        """处理所有网站"""
        # 串行或并行处理
        pass
        
    def get_all_chinese_content(self) -> List[Dict[str, Any]]:
        """获取所有中文内容"""
        pass
```

### 3.4 整合器类

#### 3.4.1 NewsIntegrationAgent（新闻整合智能体）

```python
class NewsIntegrationAgent:
    """整合所有新闻并生成报告"""
    
    def __init__(self, model_name: str, api_key: str):
        self.llm = ...
        
    def integrate(self, all_chinese_content: List[Dict[str, Any]]) -> str:
        """整合所有内容并生成报告"""
        # 1. 分析所有内容
        # 2. 识别共同主题
        # 3. 提取关键信息
        # 4. 生成综合报告
        pass
```

## 四、工作流程设计

### 4.1 单个网站处理流程

```
┌─────────────┐
│ 检查缓存     │
│ - 缓存存在？ │
│ - 缓存有效？ │
└──────┬──────┘
       ↓
   是/否
   ↙    ↘
┌────┐  ┌─────────────┐
│使用│  │ 抓取网页内容 │
│缓存│  │ - 网络请求   │
└─┬──┘  │ - 保存缓存   │
   │    └──────┬──────┘
   └──────┬────┘
          ↓
┌─────────────┐
│  感知阶段    │
│ - 提取新闻   │
│ - 识别关键信息│
└──────┬──────┘
       ↓
┌─────────────┐
│  建模阶段    │
│ - 构建世界模型│
│ - 理解内容   │
└──────┬──────┘
       ↓
┌─────────────┐
│ 中文转换     │
│ - 翻译内容   │
│ - 保持结构   │
└──────┬──────┘
       ↓
   输出结果
```

### 4.2 整体处理流程

```
初始化阶段
  ↓
┌──────────────────────────────┐
│ 创建所有网站感知器实例        │
│ - 根据网站类型选择感知器类    │
│ - 配置模型和参数              │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 依次处理每个网站              │
│ for perceptor in perceptors: │
│   result = perceptor.process()│
│   results.append(result)     │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 收集所有中文内容              │
│ all_content = []             │
│ for result in results:       │
│   all_content.append(        │
│     result['chinese_content']│
│   )                          │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 整合与思考阶段                │
│ - 分析所有内容                │
│ - 识别共同主题                │
│ - 提取关键信息                │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 生成最终报告                  │
│ - 综合新闻报告                │
│ - 包含所有来源的关键信息      │
└──────────┬───────────────────┘
           ↓
        完成
```

## 五、技术选型

### 5.1 网页内容获取

- **主要方案**：使用 `requests` + `BeautifulSoup4` 或 `selenium`
- **备选方案**：使用 `langchain` 的网页加载器（如 `WebBaseLoader`）
- **特殊处理**：对于需要JavaScript渲染的网站，使用 `selenium` 或 `playwright`

### 5.2 内容提取

- **HTML解析**：BeautifulSoup4
- **文本清洗**：自定义清洗函数，去除广告、导航等无关内容
- **内容结构化**：提取标题、正文、发布时间等

### 5.3 大模型调用

- **主要模型**：通义千问（Tongyi/Qwen）
- **多模型支持**：支持配置不同的模型（如Qwen-Turbo、Qwen-Max等）
- **API调用**：使用 `langchain_community.llms.Tongyi`

### 5.4 工作流管理

- **框架**：LangGraph（参考现有实现）
- **状态管理**：使用TypedDict定义状态
- **错误处理**：每个阶段都有错误处理机制

## 六、数据结构设计

### 6.1 感知阶段输出

```python
class PerceptionOutput(BaseModel):
    """感知阶段输出"""
    website_name: str
    url: str
    extracted_news: List[Dict[str, str]]  # 新闻列表，包含标题、内容、时间等
    key_topics: List[str]  # 关键主题
    important_info: Dict[str, Any]  # 重要信息
    extraction_time: str  # 提取时间
```

### 6.2 建模阶段输出

```python
class WorldModelOutput(BaseModel):
    """世界模型输出"""
    website_name: str
    content_summary: str  # 内容摘要
    main_themes: List[str]  # 主要主题
    sentiment: str  # 情绪倾向
    key_insights: List[str]  # 关键洞察
    related_entities: List[str]  # 相关实体（人物、公司、事件等）
```

### 6.3 中文转换输出

```python
class ChineseContentOutput(BaseModel):
    """中文内容输出"""
    website_name: str
    url: str
    chinese_summary: str  # 中文摘要
    chinese_news: List[Dict[str, str]]  # 中文新闻列表
    chinese_insights: List[str]  # 中文洞察
    source_language: str  # 原始语言
```

### 6.4 最终报告结构

```python
class FinalReport(BaseModel):
    """最终报告"""
    report_title: str
    generation_time: str
    sources: List[str]  # 来源网站列表
    executive_summary: str  # 执行摘要
    main_sections: List[Dict[str, str]]  # 主要章节
    key_findings: List[str]  # 关键发现
    trends_analysis: str  # 趋势分析
    conclusion: str  # 结论
```

## 七、提示词设计

### 7.1 感知阶段提示词

```python
PERCEPTION_PROMPT = """你是一个专业的新闻分析师，请从以下网页内容中提取最新的新闻和信息：

网站名称: {website_name}
网站URL: {url}
网页内容: {content}

请提取以下信息：
1. 最新的新闻标题和内容（至少15条）
2. 关键主题和话题
3. 重要信息（数据、事件、人物等）
4. 新闻发布时间（如果可获取）

输出格式为JSON，包含：
- extracted_news: 新闻列表
- key_topics: 关键主题列表
- important_info: 重要信息字典
"""
```

### 7.2 建模阶段提示词

```python
MODELING_PROMPT = """你是一个资深的内容分析师，请根据以下提取的新闻和信息，构建内容理解模型：

网站名称: {website_name}
提取的新闻和信息: {perception_data}

请构建一个全面的内容理解模型，包括：
1. 内容摘要
2. 主要主题
3. 情绪倾向
4. 关键洞察
5. 相关实体（人物、公司、事件等）

输出格式为JSON。
"""
```

### 7.3 中文转换提示词

```python
TRANSLATION_PROMPT = """你是一个专业的翻译和内容转换专家，请将以下内容转换为中文，同时保持原有的结构和含义：

原始语言: {source_language}
网站名称: {website_name}
世界模型内容: {world_model}

请将所有内容转换为中文，包括：
1. 摘要
2. 新闻标题和内容
3. 洞察和分析
4. 保持专业术语的准确性

输出格式为JSON，所有文本字段都应为中文。
"""
```

### 7.4 整合阶段提示词

```python
INTEGRATION_PROMPT = """你是一个资深的新闻编辑和内容整合专家，请根据以下来自多个网站的中文内容，生成一份综合新闻报告：

来源网站数量: {source_count}
各网站内容: {all_chinese_content}

请生成一份结构完整、逻辑清晰的综合新闻报告，包括：
1. 报告标题和摘要
2. 主要新闻事件（按重要性排序）
3. 共同主题和趋势分析
4. 不同来源的视角对比
5. 关键发现和洞察
6. 结论和建议

报告应当客观、全面，整合所有来源的关键信息。
"""
```

## 八、网站分类与配置

### 8.1 网站分类

根据 `web_sites.md` 中的22个网站，分类如下：

#### 财经类
- Bloomberg (https://www.bloomberg.com/)
- Financial Times
- 雪球 (https://xueqiu.com/)
- 经济时报 (https://economictimes.indiatimes.com/)
- Rediff Money (https://money.rediff.com/)
- 证券时报 (https://www.stcn.com/)

#### 科技类
- Medium
- 齐思
- There's An AI For That

#### 综合新闻类
- 南华早报 (https://www.scmp.com/)
- 新华网 (https://www.news.cn/)
- 人民网 (http://www.people.com.cn/)
- 南方网 (https://www.southcn.com/)
- 求是网 (http://www.qstheory.cn/)
- 广东省政府 (https://www.gd.gov.cn/gdywdt/index.html)
- The Messenger (News | Them)

#### 论坛/社区类
- Reddit (https://www.reddit.com/)
- Discuss.com.hk (https://www.discuss.com.hk/)
- Mobile01

#### 其他
- HelpGuide.org

### 8.2 模型配置建议

- **中文网站**：使用 Qwen-Turbo（对中文支持好）
- **英文财经网站**：使用 Qwen-Max（需要更强的分析能力）
- **论坛类**：使用 Qwen-Turbo（内容相对简单）
- **多语言网站**：使用 Qwen-Max（需要多语言理解能力）

## 九、错误处理与容错机制

### 9.1 网页获取失败
- 重试机制（最多3次）
- 记录失败网站，继续处理其他网站
- 在最终报告中标注数据来源缺失

### 9.2 内容提取失败
- 使用备用提取策略
- 记录原始HTML用于调试
- 返回部分提取结果

### 9.3 模型调用失败
- 重试机制
- 降级到备用模型
- 记录错误但继续处理

### 9.4 中文转换失败
- 保留原始语言内容
- 在报告中标注语言信息
- 尝试使用翻译API作为备选

## 十、性能优化

### 10.1 并行处理
- 对于独立的网站，可以并行处理
- 使用 `concurrent.futures.ThreadPoolExecutor` 或 `asyncio`
- 注意API调用频率限制

### 10.2 缓存机制

#### 10.2.1 缓存策略

- **存储位置**：所有网页内容备份存储在 `cache/` 文件夹下
- **文件命名规则**：`{网站名称}_{URL的MD5哈希值}.html`
  - 例如：`Bloomberg_a1b2c3d4e5f6.html`
- **缓存有效期**：默认24小时，可配置
- **缓存检查流程**：
  1. 检查缓存文件是否存在
  2. 检查缓存文件是否过期（基于文件修改时间）
  3. 如果缓存有效，直接使用缓存内容
  4. 如果缓存无效或不存在，重新抓取并更新缓存

#### 10.2.2 缓存实现细节

```python
# 缓存文件结构
cache/
├── Bloomberg_a1b2c3d4e5f6.html
├── 雪球_x1y2z3w4v5u6.html
├── Reddit_r1s2t3u4v5w6.html
└── ...

# 缓存元数据（可选，存储额外信息）
cache/
├── metadata.json  # 存储缓存文件的元信息
└── ...
```

#### 10.2.3 缓存管理功能

- **自动缓存**：每次抓取网页后自动保存到缓存
- **缓存命中**：优先使用缓存，减少网络请求
- **缓存更新**：缓存过期后自动更新
- **手动清理**：支持手动清理过期缓存或全部缓存
- **缓存统计**：记录缓存命中率和节省的网络请求次数

#### 10.2.4 缓存配置

在配置文件中可以设置：
- `cache_enabled`: 是否启用缓存（默认：true）
- `cache_max_age_hours`: 缓存最大有效期（默认：24小时）
- `cache_dir`: 缓存目录路径（默认：`cache/`）
- `force_refresh`: 强制刷新缓存（忽略缓存）

### 10.3 增量更新
- 记录上次处理时间
- 只处理新内容
- 支持增量报告生成

## 十一、实现步骤

### 阶段一：基础框架
1. 实现 `WebsitePerceptorBase` 基类
2. 实现网页内容获取功能
3. 实现基础的感知和建模流程

### 阶段二：具体感知器
1. 实现 `FinancialNewsPerceptor`
2. 实现 `TechNewsPerceptor`
3. 实现 `GeneralNewsPerceptor`
4. 实现 `ForumPerceptor`

### 阶段三：管理器与整合
1. 实现 `WebsitePerceptorManager`
2. 实现 `NewsIntegrationAgent`
3. 实现最终报告生成

### 阶段四：优化与测试
1. 添加错误处理
2. 性能优化
3. 测试所有网站
4. 完善文档

## 十二、依赖项

需要添加的依赖：
- `requests`: 网页请求
- `beautifulsoup4`: HTML解析
- `selenium` 或 `playwright`: JavaScript渲染（如需要）
- `lxml`: HTML解析器
- `html2text`: HTML转文本（可选）

## 十三、配置文件设计

建议创建 `website_config.json` 配置文件：

```json
{
  "websites": [
    {
      "name": "Bloomberg",
      "url": "https://www.bloomberg.com/",
      "type": "financial",
      "model": "Qwen-Max",
      "language": "en",
      "description": "彭博社"
    },
    {
      "name": "雪球",
      "url": "https://xueqiu.com/",
      "type": "financial",
      "model": "Qwen-Turbo",
      "language": "zh",
      "description": "雪球网"
    }
  ],
  "api_keys": {
    "dashscope": "your-api-key"
  },
  "settings": {
    "parallel_processing": false,
    "max_retries": 3,
    "timeout": 30,
    "cache_enabled": true,
    "cache_max_age_hours": 24,
    "cache_dir": "cache",
    "force_refresh": false
  }
}
```

## 十四、输出示例

### 单个网站输出示例

```json
{
  "website_name": "Bloomberg",
  "url": "https://www.bloomberg.com/",
  "chinese_summary": "彭博社今日主要报道了...",
  "chinese_news": [
    {
      "title": "美联储维持利率不变",
      "content": "...",
      "time": "2025-01-XX"
    }
  ],
  "chinese_insights": [
    "市场对美联储政策反应积极",
    "科技股表现强劲"
  ]
}
```

### 最终报告示例

```
# 综合新闻报告

**生成时间**: 2025-01-XX XX:XX:XX
**来源网站**: 22个

## 执行摘要
...

## 主要新闻事件
1. ...
2. ...

## 趋势分析
...

## 关键发现
...

## 结论
...
```

## 十五、注意事项

1. **API限制**：注意大模型API的调用频率和配额限制
2. **网页抓取**：遵守网站的robots.txt和使用条款
3. **内容版权**：注意内容的版权问题，仅用于研究目的
4. **数据隐私**：不要存储敏感个人信息
5. **网络稳定性**：处理网络不稳定和网站访问限制的情况
6. **多语言支持**：确保模型能够处理多种语言
7. **内容准确性**：大模型可能产生幻觉，需要验证关键信息

## 十六、缓存机制详细设计

### 16.1 缓存文件命名规则

- **格式**：`{网站名称}_{URL的MD5哈希值}.html`
- **示例**：
  - Bloomberg: `Bloomberg_a1b2c3d4e5f67890123456789012.html`
  - 雪球: `雪球_x1y2z3w4v5u67890123456789012.html`
- **优势**：
  - 文件名唯一，避免冲突
  - 包含网站名称，便于识别
  - 使用MD5哈希，处理特殊字符

### 16.2 缓存文件存储结构

```
cache/
├── Bloomberg_a1b2c3d4e5f6.html          # 网页HTML内容
├── 雪球_x1y2z3w4v5u6.html
├── Reddit_r1s2t3u4v5w6.html
├── metadata.json                         # 缓存元数据（可选）
└── .gitignore                           # 忽略缓存文件（建议）
```

### 16.3 缓存元数据（可选）

```json
{
  "cache_files": [
    {
      "filename": "Bloomberg_a1b2c3d4e5f6.html",
      "url": "https://www.bloomberg.com/",
      "website_name": "Bloomberg",
      "cached_at": "2025-01-XX 10:00:00",
      "file_size": 123456,
      "expires_at": "2025-01-XX 10:00:00"
    }
  ],
  "statistics": {
    "total_cached": 22,
    "total_size_mb": 12.5,
    "cache_hits": 150,
    "cache_misses": 30
  }
}
```

### 16.4 缓存使用流程

```python
def fetch_content_with_cache(self, use_cache=True, max_age_hours=24):
    """带缓存的网页内容获取"""
    cache_path = self.get_cache_path()
    
    # 1. 检查是否使用缓存
    if use_cache:
        cached_content = self.load_from_cache(cache_path, max_age_hours)
        if cached_content:
            print(f"[缓存命中] {self.name}")
            return cached_content
    
    # 2. 缓存未命中，抓取网页
    print(f"[抓取网页] {self.name}")
    content = self._fetch_from_web()  # 实际抓取方法
    
    # 3. 保存到缓存
    self.save_to_cache(content, cache_path)
    print(f"[缓存已保存] {self.name}")
    
    return content
```

### 16.5 缓存清理策略

- **自动清理**：定期清理过期缓存（可配置清理周期）
- **手动清理**：提供命令行工具清理缓存
- **按需清理**：支持清理特定网站的缓存
- **大小限制**：设置缓存目录大小限制，超出时清理最旧的缓存

### 16.6 缓存优势

1. **减少网络请求**：避免重复抓取相同网页
2. **提高处理速度**：直接读取本地文件，速度快
3. **降低被封风险**：减少对目标网站的请求频率
4. **离线处理**：即使网络断开，也能使用缓存内容
5. **调试方便**：可以查看缓存的原始HTML内容

### 16.7 注意事项

1. **缓存目录管理**：建议将 `cache/` 目录添加到 `.gitignore`
2. **缓存有效期**：根据新闻更新频率设置合理的缓存时间
3. **磁盘空间**：定期清理缓存，避免占用过多磁盘空间
4. **缓存一致性**：确保缓存内容与网页内容一致
5. **并发安全**：多进程/多线程环境下注意缓存文件的读写安全

## 十七、扩展方向

1. **实时监控**：定期自动抓取和更新
2. **主题过滤**：支持按主题过滤新闻
3. **情感分析**：深入的情感分析
4. **可视化**：生成图表和可视化报告
5. **数据库存储**：将结果存储到数据库
6. **Web界面**：提供Web界面查看报告
7. **API服务**：提供API接口供其他系统调用

