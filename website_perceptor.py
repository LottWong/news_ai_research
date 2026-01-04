#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网站感知器模块

实现网站感知器基类和具体实现类，用于从不同网站获取和感知新闻内容。
新流程：首页筛选链接 -> 获取链接内容 -> 感知并缓存
"""

import os
import json
import hashlib
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

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
        
    def get_perception_cache_path(self, article_url: str) -> str:
        """获取感知结果的缓存文件路径"""
        # 使用文章URL的hash值作为文件名
        url_hash = hashlib.md5(article_url.encode()).hexdigest()
        # 清理网站名称，移除特殊字符
        safe_name = re.sub(r'[^\w\-_\.]', '_', self.name)
        cache_subdir = os.path.join(self.cache_dir, safe_name)
        os.makedirs(cache_subdir, exist_ok=True)
        return os.path.join(cache_subdir, f"{url_hash}.json")
    
    def load_perception_from_cache(self, cache_path: str) -> Optional[Dict[str, Any]]:
        """从缓存加载感知结果"""
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
                return json.load(f)
        except Exception as e:
            print(f"[警告] 读取缓存失败: {str(e)}")
            return None
    
    def save_perception_to_cache(self, perception_data: Dict[str, Any], cache_path: str):
        """保存感知结果到缓存"""
        if not self.cache_enabled:
            return
            
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(perception_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存缓存失败: {str(e)}")
    
    def _fetch_from_web(self, url: str) -> str:
        """从网络抓取网页内容"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except Exception as e:
            print(f"[错误] 抓取失败 {url}: {str(e)}")
            raise
    
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
    
    def extract_links_from_homepage(self, html_content: str) -> List[Dict[str, str]]:
        """从首页HTML中提取所有链接"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        # 提取所有a标签
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            title = a_tag.get_text().strip()
            
            if not href or not title:
                continue
            
            # 转换为绝对URL
            absolute_url = urljoin(self.url, href)
            
            # 过滤掉非本站链接和无效链接
            parsed_base = urlparse(self.url)
            parsed_link = urlparse(absolute_url)
            
            if parsed_link.netloc and parsed_link.netloc != parsed_base.netloc:
                continue  # 跳过外部链接
            
            if any(skip in absolute_url.lower() for skip in ['javascript:', 'mailto:', '#', 'void(0)']):
                continue
            
            # 清理标题
            title = re.sub(r'\s+', ' ', title)
            if len(title) < 5:  # 标题太短，可能是导航链接
                continue
            
            links.append({
                "title": title[:200],  # 限制标题长度
                "url": absolute_url
            })
        
        # 去重（基于URL）
        seen_urls = set()
        unique_links = []
        for link in links:
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                unique_links.append(link)
        
        return unique_links
    
    def filter_important_links(self, links: List[Dict[str, str]], homepage_content: str) -> List[Dict[str, str]]:
        """使用大模型筛选重要且实时的链接（15-20条）"""
        print(f"[筛选链接] {self.name}: 从 {len(links)} 个链接中筛选...")
        
        # 限制链接数量，避免超出token限制
        links_to_analyze = links[:100]  # 最多分析100个链接
        
        prompt = ChatPromptTemplate.from_template("""你是一个专业的新闻编辑，请从以下链接列表中筛选出15-20条最重要且实时的新闻链接。

网站名称: {website_name}
网站URL: {url}
首页内容摘要: {homepage_summary}

链接列表:
{links_list}

请根据以下标准筛选：
1. 新闻的重要性和时效性
2. 内容的新闻价值
3. 避免重复或相似的内容
4. 优先选择最新、最热门的新闻

输出格式为JSON数组，每个元素包含：
- title: 链接标题
- url: 链接URL
- reason: 选择理由

请输出15-20条链接，按重要性排序。
""")
        
        # 构建链接列表文本
        links_text = "\n".join([
            f"{i+1}. {link['title']} - {link['url']}"
            for i, link in enumerate(links_to_analyze)
        ])
        
        # 构建输入
        input_data = {
            "website_name": self.name,
            "url": self.url,
            "homepage_summary": self.clean_html(homepage_content)[:5000],  # 首页摘要
            "links_list": links_text
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            
            # 确保返回的是列表
            if isinstance(result, dict):
                if "links" in result:
                    filtered_links = result["links"]
                elif "selected_links" in result:
                    filtered_links = result["selected_links"]
                else:
                    # 尝试从字典值中提取列表
                    filtered_links = [v for v in result.values() if isinstance(v, list)]
                    if filtered_links:
                        filtered_links = filtered_links[0]
                    else:
                        filtered_links = []
            elif isinstance(result, list):
                filtered_links = result
            else:
                filtered_links = []
            
            # 验证并规范化链接格式
            normalized_links = []
            for link in filtered_links[:20]:  # 最多20条
                if isinstance(link, dict):
                    # 确保有title和url字段
                    if "url" in link or "link" in link:
                        normalized_links.append({
                            "title": link.get("title", link.get("name", "")),
                            "url": link.get("url", link.get("link", "")),
                            "reason": link.get("reason", "")
                        })
                elif isinstance(link, str):
                    # 如果是字符串，尝试解析
                    continue
            
            print(f"[筛选完成] {self.name}: 筛选出 {len(normalized_links)} 条重要链接")
            return normalized_links
            
        except Exception as e:
            print(f"[错误] 筛选链接失败 {self.name}: {str(e)}")
            # 如果筛选失败，返回前15个链接
            return links[:15]
    
    def perception_single_article(self, article_url: str, article_title: str, force_refresh: bool = False) -> Dict[str, Any]:
        """感知单篇文章内容"""
        cache_path = self.get_perception_cache_path(article_url)
        
        # 检查缓存
        if not force_refresh:
            cached_perception = self.load_perception_from_cache(cache_path)
            if cached_perception:
                print(f"  [缓存命中] {article_title[:50]}...")
                return cached_perception
        
        # 获取文章内容
        print(f"  [获取内容] {article_title[:50]}...")
        try:
            html_content = self._fetch_from_web(article_url)
            clean_text = self.clean_html(html_content)
        except Exception as e:
            print(f"  [错误] 获取内容失败: {str(e)}")
            return {
                "title": article_title,
                "url": article_url,
                "success": False,
                "error": str(e)
            }
        
        # 感知文章内容
        print(f"  [感知内容] {article_title[:50]}...")
        perception_data = self._perception_article_content(article_url, article_title, clean_text)
        
        # 保存到缓存
        self.save_perception_to_cache(perception_data, cache_path)
        
        return perception_data
    
    def _perception_article_content(self, article_url: str, article_title: str, content: str) -> Dict[str, Any]:
        """感知文章内容（子类可重写）"""
        prompt = ChatPromptTemplate.from_template("""你是一个专业的新闻分析师，请分析以下文章内容：

文章标题: {article_title}
文章URL: {article_url}
文章内容: {content}

请提取以下信息：
1. 文章摘要（200字以内）
2. 关键信息（数据、事件、人物等）
3. 主要观点和结论
4. 相关主题和标签

输出格式为JSON，包含：
- summary: 文章摘要
- key_info: 关键信息列表
- main_points: 主要观点列表
- topics: 相关主题列表
""")
        
        input_data = {
            "article_title": article_title,
            "article_url": article_url,
            "content": content[:30000]  # 限制长度
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            
            # 添加元数据
            result["title"] = article_title
            result["url"] = article_url
            result["website_name"] = self.name
            result["perception_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["success"] = True
            
            return result
        except Exception as e:
            print(f"  [错误] 感知失败: {str(e)}")
            return {
                "title": article_title,
                "url": article_url,
                "website_name": self.name,
                "success": False,
                "error": str(e)
            }
    
    def modeling(self, all_perceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """建模阶段：构建内部世界模型"""
        print(f"[建模阶段] {self.name}")
        
        prompt = ChatPromptTemplate.from_template("""你是一个资深的内容分析师，请根据以下多篇文章的感知结果，构建内容理解模型：

网站名称: {website_name}
文章数量: {article_count}
感知结果: {perceptions}

请构建一个全面的内容理解模型，包括：
1. 整体内容摘要
2. 主要主题和趋势
3. 情绪倾向
4. 关键洞察
5. 相关实体（人物、公司、事件等）

输出格式为JSON，包含：
- content_summary: 整体内容摘要
- main_themes: 主要主题列表
- sentiment: 情绪倾向
- key_insights: 关键洞察列表
- related_entities: 相关实体列表
""")
        
        input_data = {
            "website_name": self.name,
            "article_count": len(all_perceptions),
            "perceptions": json.dumps(all_perceptions, ensure_ascii=False, indent=2)
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
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
    
    def translate_to_chinese(self, world_model: Dict[str, Any], all_perceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将世界模型转换为中文"""
        print(f"[中文转换] {self.name}")
        
        # 如果已经是中文，直接返回
        if self.language == "zh":
            return {
                "website_name": self.name,
                "url": self.url,
                "chinese_summary": world_model.get("content_summary", ""),
                "chinese_articles": [
                    {
                        "title": p.get("title", ""),
                        "url": p.get("url", ""),
                        "summary": p.get("summary", ""),
                        "key_info": p.get("key_info", [])
                    }
                    for p in all_perceptions if p.get("success")
                ],
                "chinese_insights": world_model.get("key_insights", []),
                "source_language": "zh"
            }
        
        # 准备提示
        prompt = ChatPromptTemplate.from_template("""你是一个专业的翻译和内容转换专家，请将以下内容转换为中文，同时保持原有的结构和含义：

原始语言: {source_language}
网站名称: {website_name}
世界模型: {world_model}
文章感知结果: {perceptions}

请将所有内容转换为中文，包括：
1. 摘要
2. 文章标题和摘要
3. 洞察和分析
4. 保持专业术语的准确性

输出格式为JSON，包含：
- chinese_summary: 中文摘要
- chinese_articles: 中文文章列表（包含title, url, summary, key_info）
- chinese_insights: 中文洞察列表
所有文本字段都应为中文。
""")
        
        input_data = {
            "source_language": self.language,
            "website_name": self.name,
            "world_model": json.dumps(world_model, ensure_ascii=False, indent=2),
            "perceptions": json.dumps(all_perceptions, ensure_ascii=False, indent=2)
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
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
                "chinese_articles": [],
                "chinese_insights": [],
                "source_language": self.language,
                "error": str(e)
            }
    
    def process(self, force_refresh: bool = False) -> Dict[str, Any]:
        """完整处理流程"""
        try:
            # 1. 获取首页内容
            print(f"\n[处理网站] {self.name}")
            print(f"[获取首页] {self.url}")
            homepage_content = self._fetch_from_web(self.url)
            
            # 2. 提取链接
            print(f"[提取链接] {self.name}")
            all_links = self.extract_links_from_homepage(homepage_content)
            print(f"  找到 {len(all_links)} 个链接")
            
            # 3. 筛选重要链接
            filtered_links = self.filter_important_links(all_links, homepage_content)
            
            if not filtered_links:
                print(f"[警告] {self.name}: 未筛选到有效链接")
                return {
                    "website_name": self.name,
                    "url": self.url,
                    "success": False,
                    "error": "未筛选到有效链接"
                }
            
            # 4. 对每个链接进行感知（带缓存）
            print(f"[感知文章] {self.name}: 处理 {len(filtered_links)} 篇文章")
            all_perceptions = []
            for i, link in enumerate(filtered_links, 1):
                article_url = link.get("url", link.get("link", ""))
                article_title = link.get("title", "")
                
                if not article_url or not article_title:
                    print(f"  [{i}/{len(filtered_links)}] [跳过] 链接信息不完整")
                    continue
                
                print(f"  [{i}/{len(filtered_links)}]", end=" ")
                perception = self.perception_single_article(
                    article_url=article_url,
                    article_title=article_title,
                    force_refresh=force_refresh
                )
                if perception.get("success"):
                    all_perceptions.append(perception)
            
            if not all_perceptions:
                print(f"[警告] {self.name}: 没有成功感知的文章")
                return {
                    "website_name": self.name,
                    "url": self.url,
                    "success": False,
                    "error": "没有成功感知的文章"
                }
            
            # 5. 建模
            world_model = self.modeling(all_perceptions)
            
            # 6. 转换为中文
            chinese_content = self.translate_to_chinese(world_model, all_perceptions)
            
            # 7. 返回结果
            return {
                "website_name": self.name,
                "url": self.url,
                "filtered_links": filtered_links,
                "perceptions": all_perceptions,
                "world_model": world_model,
                "chinese_content": chinese_content,
                "success": True
            }
        except Exception as e:
            print(f"[错误] 处理失败 {self.name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "website_name": self.name,
                "url": self.url,
                "success": False,
                "error": str(e)
            }


class FinancialNewsPerceptor(WebsitePerceptorBase):
    """财经新闻感知器"""
    
    def _perception_article_content(self, article_url: str, article_title: str, content: str) -> Dict[str, Any]:
        """财经新闻专用感知方法"""
        prompt = ChatPromptTemplate.from_template("""你是一个专业的财经新闻分析师，请分析以下财经文章内容：

文章标题: {article_title}
文章URL: {article_url}
文章内容: {content}

请特别关注：
1. 文章摘要（200字以内）
2. 股票、汇率、经济数据等关键指标
3. 市场动态和趋势
4. 重要公司新闻和财报信息
5. 政策变化和经济事件

输出格式为JSON，包含：
- summary: 文章摘要
- key_info: 关键信息列表（包含经济数据、市场指标等）
- main_points: 主要观点列表
- topics: 相关主题列表
""")
        
        input_data = {
            "article_title": article_title,
            "article_url": article_url,
            "content": content[:30000]
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            result["title"] = article_title
            result["url"] = article_url
            result["website_name"] = self.name
            result["perception_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["success"] = True
            return result
        except Exception as e:
            return {
                "title": article_title,
                "url": article_url,
                "website_name": self.name,
                "success": False,
                "error": str(e)
            }


class TechNewsPerceptor(WebsitePerceptorBase):
    """科技新闻感知器"""
    
    def _perception_article_content(self, article_url: str, article_title: str, content: str) -> Dict[str, Any]:
        """科技新闻专用感知方法"""
        prompt = ChatPromptTemplate.from_template("""你是一个专业的科技新闻分析师，请分析以下科技文章内容：

文章标题: {article_title}
文章URL: {article_url}
文章内容: {content}

请特别关注：
1. 文章摘要（200字以内）
2. AI、机器学习、大数据等技术趋势
3. 产品发布和技术突破
4. 行业动态和公司新闻
5. 技术分析和评测

输出格式为JSON，包含：
- summary: 文章摘要
- key_info: 关键信息列表（包含技术细节、产品信息等）
- main_points: 主要观点列表
- topics: 相关主题列表
""")
        
        input_data = {
            "article_title": article_title,
            "article_url": article_url,
            "content": content[:30000]
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            result["title"] = article_title
            result["url"] = article_url
            result["website_name"] = self.name
            result["perception_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["success"] = True
            return result
        except Exception as e:
            return {
                "title": article_title,
                "url": article_url,
                "website_name": self.name,
                "success": False,
                "error": str(e)
            }


class GeneralNewsPerceptor(WebsitePerceptorBase):
    """综合新闻感知器"""
    pass  # 使用基类的默认实现


class ForumPerceptor(WebsitePerceptorBase):
    """论坛感知器"""
    
    def _perception_article_content(self, article_url: str, article_title: str, content: str) -> Dict[str, Any]:
        """论坛专用感知方法"""
        prompt = ChatPromptTemplate.from_template("""你是一个专业的论坛内容分析师，请分析以下论坛讨论内容：

话题标题: {article_title}
话题URL: {article_url}
讨论内容: {content}

请特别关注：
1. 话题摘要（200字以内）
2. 用户观点和评论趋势
3. 热点事件和争议话题
4. 讨论的焦点和趋势

输出格式为JSON，包含：
- summary: 话题摘要
- key_info: 关键信息列表（包含热门讨论、用户观点等）
- main_points: 主要观点列表
- topics: 相关主题列表
""")
        
        input_data = {
            "article_title": article_title,
            "article_url": article_url,
            "content": content[:30000]
        }
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke(input_data)
            result["title"] = article_title
            result["url"] = article_url
            result["website_name"] = self.name
            result["perception_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["success"] = True
            return result
        except Exception as e:
            return {
                "title": article_title,
                "url": article_url,
                "website_name": self.name,
                "success": False,
                "error": str(e)
            }
