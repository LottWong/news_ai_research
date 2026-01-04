#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻管理器模块

管理多个网站感知器，协调处理流程，收集结果。
"""

import json
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from website_perceptor import (
    WebsitePerceptorBase,
    FinancialNewsPerceptor,
    TechNewsPerceptor,
    GeneralNewsPerceptor,
    ForumPerceptor
)


class WebsitePerceptorManager:
    """网站感知器管理器"""
    
    def __init__(self, cache_dir: str = "cache", cache_enabled: bool = True, cache_max_age_hours: int = 24):
        self.perceptors: List[WebsitePerceptorBase] = []
        self.cache_dir = cache_dir
        self.cache_enabled = cache_enabled
        self.cache_max_age_hours = cache_max_age_hours
        self.results: List[Dict[str, Any]] = []
        
    def create_perceptor(
        self,
        url: str,
        name: str,
        website_type: str,
        model_name: str,
        api_key: str,
        language: str = "auto",
        description: str = ""
    ) -> WebsitePerceptorBase:
        """根据网站类型创建感知器"""
        
        base_params = {
            "url": url,
            "name": name,
            "model_name": model_name,
            "api_key": api_key,
            "language": language,
            "description": description,
            "cache_dir": self.cache_dir,
            "cache_enabled": self.cache_enabled,
            "cache_max_age_hours": self.cache_max_age_hours
        }
        
        if website_type == "financial":
            return FinancialNewsPerceptor(**base_params)
        elif website_type == "tech":
            return TechNewsPerceptor(**base_params)
        elif website_type == "forum":
            return ForumPerceptor(**base_params)
        else:
            return GeneralNewsPerceptor(**base_params)
    
    def add_perceptor(self, perceptor: WebsitePerceptorBase):
        """添加感知器"""
        self.perceptors.append(perceptor)
    
    def add_perceptor_from_config(self, config: Dict[str, Any], api_key: str):
        """从配置添加感知器"""
        perceptor = self.create_perceptor(
            url=config["url"],
            name=config["name"],
            website_type=config.get("type", "general"),
            model_name=config.get("model", "Qwen-Turbo"),
            api_key=api_key,
            language=config.get("language", "auto"),
            description=config.get("description", "")
        )
        self.add_perceptor(perceptor)
    
    def process_all(self, parallel: bool = False, max_workers: int = 3, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """处理所有网站"""
        self.results = []
        
        if parallel:
            return self._process_parallel(max_workers=max_workers, force_refresh=force_refresh)
        else:
            return self._process_sequential(force_refresh=force_refresh)
    
    def _process_sequential(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """串行处理"""
        results = []
        for i, perceptor in enumerate(self.perceptors, 1):
            print(f"\n[{i}/{len(self.perceptors)}] 处理网站: {perceptor.name}")
            try:
                result = perceptor.process(use_cache=True, force_refresh=force_refresh)
                results.append(result)
            except Exception as e:
                print(f"[错误] 处理失败 {perceptor.name}: {str(e)}")
                results.append({
                    "website_name": perceptor.name,
                    "url": perceptor.url,
                    "success": False,
                    "error": str(e)
                })
        self.results = results
        return results
    
    def _process_parallel(self, max_workers: int = 3, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """并行处理"""
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_perceptor = {
                executor.submit(perceptor.process, use_cache=True, force_refresh=force_refresh): perceptor
                for perceptor in self.perceptors
            }
            
            # 收集结果
            for i, future in enumerate(as_completed(future_to_perceptor), 1):
                perceptor = future_to_perceptor[future]
                print(f"\n[{i}/{len(self.perceptors)}] 完成: {perceptor.name}")
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"[错误] 处理失败 {perceptor.name}: {str(e)}")
                    results.append({
                        "website_name": perceptor.name,
                        "url": perceptor.url,
                        "success": False,
                        "error": str(e)
                    })
        
        # 按原始顺序排序
        results.sort(key=lambda x: next(
            (i for i, p in enumerate(self.perceptors) if p.name == x.get("website_name", "")),
            len(self.perceptors)
        ))
        
        self.results = results
        return results
    
    def get_all_chinese_content(self) -> List[Dict[str, Any]]:
        """获取所有中文内容"""
        chinese_contents = []
        for result in self.results:
            if result.get("success") and "chinese_content" in result:
                chinese_contents.append(result["chinese_content"])
        return chinese_contents
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        total = len(self.perceptors)
        successful = sum(1 for r in self.results if r.get("success", False))
        failed = total - successful
        
        return {
            "total_websites": total,
            "successful": successful,
            "failed": failed,
            "success_rate": f"{successful/total*100:.1f}%" if total > 0 else "0%"
        }

