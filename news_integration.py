#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻整合模块

整合所有网站的中文内容，生成最终的综合新闻报告。
"""

import json
from typing import Dict, List, Any
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Tongyi
from langchain_core.output_parsers import StrOutputParser


class NewsIntegrationAgent:
    """新闻整合智能体"""
    
    def __init__(self, model_name: str = "Qwen-Max", api_key: str = ""):
        self.model_name = model_name
        self.api_key = api_key
        self.llm = Tongyi(model_name=model_name, dashscope_api_key=api_key)
    
    def integrate(self, all_chinese_content: List[Dict[str, Any]], all_results: List[Dict[str, Any]] = None) -> str:
        """整合所有内容并生成报告"""
        print("\n[整合阶段] 开始整合所有网站内容...")
        
        if not all_chinese_content:
            return "没有可用的内容进行整合。"
        
        # 收集所有文章的引用信息（标题和链接）
        article_references = []
        if all_results:
            for result in all_results:
                if result.get("success") and "chinese_content" in result:
                    chinese_content = result["chinese_content"]
                    articles = chinese_content.get("chinese_articles", [])
                    for article in articles:
                        article_references.append({
                            "title": article.get("title", ""),
                            "url": article.get("url", ""),
                            "website": result.get("website_name", "")
                        })
        
        # 准备提示
        prompt = ChatPromptTemplate.from_template("""你是一个资深的新闻编辑和内容整合专家，请根据以下来自多个网站的中文内容，生成一份综合新闻报告：

来源网站数量: {source_count}
各网站内容: {all_chinese_content}

请生成一份结构完整、逻辑清晰的综合新闻报告，包括：
1. 报告标题和摘要
2. 主要新闻事件（按重要性排序）
3. 共同主题和趋势分析
4. 不同来源的视角对比
5. 关键发现和洞察
6. 结论和建议

报告应当客观、全面，整合所有来源的关键信息。使用Markdown格式输出。
在引用具体新闻时，请使用以下格式标注来源：[标题](链接)
""")
        
        # 构建输入
        input_data = {
            "source_count": len(all_chinese_content),
            "all_chinese_content": json.dumps(all_chinese_content, ensure_ascii=False, indent=2)
        }
        
        # 调用LLM
        try:
            chain = prompt | self.llm | StrOutputParser()
            report = chain.invoke(input_data)
            
            # 添加报告头部信息和引用列表
            header = f"""# 综合新闻报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**来源网站**: {len(all_chinese_content)}个

---

"""
            
            # 添加引用列表
            if article_references:
                references_section = "\n## 参考文献\n\n"
                for ref in article_references:
                    references_section += f"- [{ref['title']}]({ref['url']}) - {ref['website']}\n"
                references_section += "\n---\n\n"
                return header + report + references_section
            
            return header + report
        except Exception as e:
            print(f"[错误] 整合阶段失败: {str(e)}")
            return f"# 综合新闻报告\n\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n**错误**: 整合过程中发生错误: {str(e)}\n"
    
    def save_report(self, report: str, filename: str = None):
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_report_{timestamp}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\n[报告已保存] {filename}")
        return filename

