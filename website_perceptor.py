#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网站感知器模块

实现网站感知器基类和具体实现类，用于从不同网站获取和感知新闻内容。
"""

import os
import json
import hashlib
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Tongyi
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser


class WebsitePerceptorBase(ABC):
    """网站感知器基类"""
    
    def __init__(
        self,
        url: str,
        name: str,
        model_name: str,
        api_key: str,
        language: str = "auto",
        description: str = "",
        cache_dir: str = "cache",
        cache_enabled: bool = True,
        cache_max_age_hours: int = 24
    ):
        self.url = url
        self.name = name
        self.model_name = model_name
        self.api_key = api_key
        self.language = language
        self.description = description
        self.cache_dir = cache_dir
        self.cache_enabled = cache_enabled
        self.cache_max_age_hours = cache_max_age_hours
        self.llm = Tongyi(model_name=model_name, dashscope_api_key=api_key)
        
    def get_cache_path(self) -> str:
        """获取缓存文件路径"""
        # 使用URL的hash值作为文件名
        url_hash = hashlib.md5(self.url.encode()).hexdigest()
        # 清理网站名称，移除特殊字符
        safe_name = re.sub(r'[^\w\-_\.]', '_', self.name)
        os.makedirs(self.cache_dir, exist_ok=True)
        return os.path.join(self.cache_dir, f"{safe_name}_{url_hash}.html")
    
    def load_from_cache(self, cache_path: str) -> Optional[str]:
        """从缓存加载内容"""
        if not self.cache_enabled:
            return None
            
        if not os.path.exists(cache_path):
            return None
        
        # 检查缓存是否过期
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - file_time > timedelta(hours=self.cache_max_age_hours):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[警告] 读取缓存失败 {self.name}: {str(e)}")
            return None
    
    def save_to_cache(self, content: str, cache_path: str):
        """保存内容到缓存"""
        if not self.cache_enabled:
            return
            
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"[警告] 保存缓存失败 {self.name}: {str(e)}")
    
    def fetch_content(self, use_cache: bool = True, force_refresh: bool = False) -> str:
        """获取网页内容（带缓存）"""
        cache_path = self.get_cache_path()
        
        # 检查缓存
        if use_cache and not force_refresh:
            cached_content = self.load_from_cache(cache_path)
            if cached_content:
                print(f"[缓存命中] {self.name}")
                return cached_content
        
        # 缓存未命中，抓取网页
        print(f"[抓取网页] {self.name}: {self.url}")
        try:
            content = self._fetch_from_web()
            # 保存到缓存
            self.save_to_cache(content, cache_path)
            print(f"[缓存已保存] {self.name}")
            return content
        except Exception as e:
            print(f"[错误] 抓取网页失败 {self.name}: {str(e)}")
            # 如果抓取失败，尝试使用过期缓存
            if use_cache and os.path.exists(cache_path):
                print(f"[使用过期缓存] {self.name}")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return f.read()
            raise
    
    def _fetch_from_web(self) -> str:
        """从网络抓取网页内容（子类可重写）"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(self.url, headers=headers, timeout=30)
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    
    def clean_html(self, html_content: str) -> str:
        """清洗HTML内容，提取主要文本"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除script和style标签
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # 提取文本
        text = soup.get_text()
        # 清理多余空白
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:50000]  # 限制长度，避免超出模型token限制
    
    def perception(self, content: str) -> Dict[str, Any]:
        """感知阶段：提取新闻和信息"""
        print(f"[感知阶段] {self.name}")
        
        # 清洗HTML
        clean_text = self.clean_html(content)
        
        # 准备提示
        prompt = ChatPromptTemplate.from_template("""你是一个专业的新闻分析师，请从以下网页内容中提取最新的新闻和信息：

网站名称: {website_name}
网站URL: {url}
网页内容: {content}

请提取以下信息：
1. 最新的新闻标题和内容（至少15条）
2. 关键主题和话题
3. 重要信息（数据、事件、人物等）
4. 新闻发布时间（如果可获取）

输出格式为JSON，包含：
- extracted_news: 新闻列表，每个新闻包含title, content, time字段
- key_topics: 关键主题列表
- important_info: 重要信息字典
""")
        
        # 构建输入
        input_data = {
            "website_name": self.name,
            "url": self.url,
            "content": clean_text[:30000]  # 限制长度
        }
        
        # 调用LLM
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            
            # 添加元数据
            result["website_name"] = self.name
            result["url"] = self.url
            result["extraction_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return result
        except Exception as e:
            print(f"[错误] 感知阶段失败 {self.name}: {str(e)}")
            # 返回基本结构
            return {
                "website_name": self.name,
                "url": self.url,
                "extracted_news": [],
                "key_topics": [],
                "important_info": {},
                "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }
    
    def modeling(self, perception_data: Dict[str, Any]) -> Dict[str, Any]:
        """建模阶段：构建内部世界模型"""
        print(f"[建模阶段] {self.name}")
        
        # 准备提示
        prompt = ChatPromptTemplate.from_template("""你是一个资深的内容分析师，请根据以下提取的新闻和信息，构建内容理解模型：

网站名称: {website_name}
提取的新闻和信息: {perception_data}

请构建一个全面的内容理解模型，包括：
1. 内容摘要
2. 主要主题
3. 情绪倾向
4. 关键洞察
5. 相关实体（人物、公司、事件等）

输出格式为JSON，包含：
- content_summary: 内容摘要
- main_themes: 主要主题列表
- sentiment: 情绪倾向
- key_insights: 关键洞察列表
- related_entities: 相关实体列表
""")
        
        # 构建输入
        input_data = {
            "website_name": self.name,
            "perception_data": json.dumps(perception_data, ensure_ascii=False, indent=2)
        }
        
        # 调用LLM
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            
            # 添加元数据
            result["website_name"] = self.name
            
            return result
        except Exception as e:
            print(f"[错误] 建模阶段失败 {self.name}: {str(e)}")
            return {
                "website_name": self.name,
                "content_summary": "",
                "main_themes": [],
                "sentiment": "neutral",
                "key_insights": [],
                "related_entities": [],
                "error": str(e)
            }
    
    def translate_to_chinese(self, world_model: Dict[str, Any], perception_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """将世界模型转换为中文"""
        print(f"[中文转换] {self.name}")
        
        # 合并感知数据和世界模型
        combined_data = {
            "world_model": world_model,
            "perception_data": perception_data or {}
        }
        
        # 如果已经是中文，直接返回
        if self.language == "zh":
            return {
                "website_name": self.name,
                "url": self.url,
                "chinese_summary": world_model.get("content_summary", ""),
                "chinese_news": (perception_data or {}).get("extracted_news", []),
                "chinese_insights": world_model.get("key_insights", []),
                "source_language": "zh"
            }
        
        # 准备提示
        prompt = ChatPromptTemplate.from_template("""你是一个专业的翻译和内容转换专家，请将以下内容转换为中文，同时保持原有的结构和含义：

原始语言: {source_language}
网站名称: {website_name}
世界模型内容: {world_model}

请将所有内容转换为中文，包括：
1. 摘要
2. 新闻标题和内容
3. 洞察和分析
4. 保持专业术语的准确性

输出格式为JSON，包含：
- chinese_summary: 中文摘要
- chinese_news: 中文新闻列表
- chinese_insights: 中文洞察列表
所有文本字段都应为中文。
""")
        
        # 构建输入
        input_data = {
            "source_language": self.language,
            "website_name": self.name,
            "world_model": json.dumps(combined_data, ensure_ascii=False, indent=2)
        }
        
        # 调用LLM
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            
            # 添加元数据
            result["website_name"] = self.name
            result["url"] = self.url
            result["source_language"] = self.language
            
            return result
        except Exception as e:
            print(f"[错误] 中文转换失败 {self.name}: {str(e)}")
            return {
                "website_name": self.name,
                "url": self.url,
                "chinese_summary": "",
                "chinese_news": [],
                "chinese_insights": [],
                "source_language": self.language,
                "error": str(e)
            }
    
    def process(self, use_cache: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
        """完整处理流程"""
        try:
            # 1. 获取内容
            content = self.fetch_content(use_cache=use_cache, force_refresh=force_refresh)
            
            # 2. 感知
            perception_data = self.perception(content)
            
            # 3. 建模
            world_model = self.modeling(perception_data)
            
            # 4. 转换为中文
            chinese_content = self.translate_to_chinese(world_model, perception_data)
            
            # 5. 返回结果
            return {
                "website_name": self.name,
                "url": self.url,
                "perception_data": perception_data,
                "world_model": world_model,
                "chinese_content": chinese_content,
                "success": True
            }
        except Exception as e:
            print(f"[错误] 处理失败 {self.name}: {str(e)}")
            return {
                "website_name": self.name,
                "url": self.url,
                "success": False,
                "error": str(e)
            }


class FinancialNewsPerceptor(WebsitePerceptorBase):
    """财经新闻感知器"""
    
    def perception(self, content: str) -> Dict[str, Any]:
        """财经新闻专用感知方法"""
        print(f"[感知阶段-财经] {self.name}")
        
        clean_text = self.clean_html(content)
        
        prompt = ChatPromptTemplate.from_template("""你是一个专业的财经新闻分析师，请从以下网页内容中提取最新的财经新闻和信息：

网站名称: {website_name}
网站URL: {url}
网页内容: {content}

请特别关注：
1. 最新的财经新闻标题和内容（至少15条）
2. 股票、汇率、经济数据等关键指标
3. 市场动态和趋势
4. 重要公司新闻和财报信息
5. 政策变化和经济事件

输出格式为JSON，包含：
- extracted_news: 新闻列表，每个新闻包含title, content, time字段
- key_topics: 关键主题列表
- important_info: 重要信息字典（包含经济数据、市场指标等）
""")
        
        input_data = {
            "website_name": self.name,
            "url": self.url,
            "content": clean_text[:30000]
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            result["website_name"] = self.name
            result["url"] = self.url
            result["extraction_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return result
        except Exception as e:
            print(f"[错误] 感知阶段失败 {self.name}: {str(e)}")
            return {
                "website_name": self.name,
                "url": self.url,
                "extracted_news": [],
                "key_topics": [],
                "important_info": {},
                "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }


class TechNewsPerceptor(WebsitePerceptorBase):
    """科技新闻感知器"""
    
    def perception(self, content: str) -> Dict[str, Any]:
        """科技新闻专用感知方法"""
        print(f"[感知阶段-科技] {self.name}")
        
        clean_text = self.clean_html(content)
        
        prompt = ChatPromptTemplate.from_template("""你是一个专业的科技新闻分析师，请从以下网页内容中提取最新的科技新闻和信息：

网站名称: {website_name}
网站URL: {url}
网页内容: {content}

请特别关注：
1. 最新的科技新闻标题和内容（至少15条）
2. AI、机器学习、大数据等技术趋势
3. 产品发布和技术突破
4. 行业动态和公司新闻
5. 技术分析和评测

输出格式为JSON，包含：
- extracted_news: 新闻列表，每个新闻包含title, content, time字段
- key_topics: 关键主题列表
- important_info: 重要信息字典（包含技术细节、产品信息等）
""")
        
        input_data = {
            "website_name": self.name,
            "url": self.url,
            "content": clean_text[:30000]
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            result["website_name"] = self.name
            result["url"] = self.url
            result["extraction_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return result
        except Exception as e:
            print(f"[错误] 感知阶段失败 {self.name}: {str(e)}")
            return {
                "website_name": self.name,
                "url": self.url,
                "extracted_news": [],
                "key_topics": [],
                "important_info": {},
                "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }


class GeneralNewsPerceptor(WebsitePerceptorBase):
    """综合新闻感知器"""
    pass  # 使用基类的默认实现


class ForumPerceptor(WebsitePerceptorBase):
    """论坛感知器"""
    
    def perception(self, content: str) -> Dict[str, Any]:
        """论坛专用感知方法"""
        print(f"[感知阶段-论坛] {self.name}")
        
        clean_text = self.clean_html(content)
        
        prompt = ChatPromptTemplate.from_template("""你是一个专业的论坛内容分析师，请从以下网页内容中提取热门话题和讨论：

网站名称: {website_name}
网站URL: {url}
网页内容: {content}

请特别关注：
1. 热门话题和讨论标题（至少15条）
2. 用户观点和评论趋势
3. 热点事件和争议话题
4. 社区关注的重点领域
5. 讨论的焦点和趋势

输出格式为JSON，包含：
- extracted_news: 话题列表，每个话题包含title, content, time字段
- key_topics: 关键主题列表
- important_info: 重要信息字典（包含热门讨论、用户观点等）
""")
        
        input_data = {
            "website_name": self.name,
            "url": self.url,
            "content": clean_text[:30000]
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            result["website_name"] = self.name
            result["url"] = self.url
            result["extraction_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return result
        except Exception as e:
            print(f"[错误] 感知阶段失败 {self.name}: {str(e)}")
            return {
                "website_name": self.name,
                "url": self.url,
                "extracted_news": [],
                "key_topics": [],
                "important_info": {},
                "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }

