#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
多源新闻感知与整合系统 - 主程序

根据配置文件，依次处理多个新闻网站，生成综合新闻报告。
"""

import json
import os
import sys
from typing import Dict, Any

from news_manager import WebsitePerceptorManager
from news_integration import NewsIntegrationAgent


def load_config(config_path: str = "website_config.json") -> Dict[str, Any]:
    """加载配置文件"""
    if not os.path.exists(config_path):
        print(f"[错误] 配置文件不存在: {config_path}")
        print("请创建 website_config.json 配置文件")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """主函数"""
    print("=" * 60)
    print("多源新闻感知与整合系统")
    print("=" * 60)
    print()
    
    # 加载配置
    print("[1/4] 加载配置文件...")
    config = load_config()
    
    # 获取API密钥
    api_key = config.get("api_keys", {}).get("dashscope", "")
    if not api_key:
        print("[错误] 未找到 dashscope API密钥")
        print("请在 website_config.json 中配置 api_keys.dashscope")
        sys.exit(1)
    
    # 获取设置
    settings = config.get("settings", {})
    parallel_processing = settings.get("parallel_processing", False)
    cache_enabled = settings.get("cache_enabled", True)
    cache_max_age_hours = settings.get("cache_max_age_hours", 24)
    cache_dir = settings.get("cache_dir", "cache")
    force_refresh = settings.get("force_refresh", False)
    
    # 创建管理器
    print("[2/4] 初始化网站感知器管理器...")
    manager = WebsitePerceptorManager(
        cache_dir=cache_dir,
        cache_enabled=cache_enabled,
        cache_max_age_hours=cache_max_age_hours
    )
    
    # 添加所有网站感知器
    websites = config.get("websites", [])
    print(f"准备处理 {len(websites)} 个网站...")
    for website_config in websites:
        try:
            manager.add_perceptor_from_config(website_config, api_key)
            print(f"  ✓ {website_config['name']} ({website_config['url']})")
        except Exception as e:
            print(f"  ✗ {website_config.get('name', 'Unknown')}: {str(e)}")
    
    print()
    
    # 处理所有网站
    print("[3/4] 处理所有网站...")
    print(f"处理模式: {'并行' if parallel_processing else '串行'}")
    print(f"缓存: {'启用' if cache_enabled else '禁用'}")
    if force_refresh:
        print("强制刷新: 是")
    print()
    
    results = manager.process_all(
        parallel=parallel_processing,
        force_refresh=force_refresh
    )
    
    # 显示统计信息
    stats = manager.get_statistics()
    print("\n" + "=" * 60)
    print("处理统计:")
    print(f"  总网站数: {stats['total_websites']}")
    print(f"  成功: {stats['successful']}")
    print(f"  失败: {stats['failed']}")
    print(f"  成功率: {stats['success_rate']}")
    print("=" * 60)
    
    # 获取所有中文内容
    print("\n[4/4] 整合所有内容并生成报告...")
    all_chinese_content = manager.get_all_chinese_content()
    
    if not all_chinese_content:
        print("[警告] 没有成功获取的中文内容，无法生成报告")
        return
    
    # 创建整合器
    integration_model = settings.get("integration_model", "Qwen-Max")
    integration_agent = NewsIntegrationAgent(
        model_name=integration_model,
        api_key=api_key
    )
    
    # 生成报告（传入所有结果以便生成引用）
    report = integration_agent.integrate(all_chinese_content, manager.results)
    
    # 保存报告
    report_filename = integration_agent.save_report(report)
    
    # 显示报告摘要
    print("\n" + "=" * 60)
    print("报告生成完成!")
    print(f"报告文件: {report_filename}")
    print("=" * 60)
    print("\n报告预览（前500字符）:")
    print("-" * 60)
    print(report[:500] + "..." if len(report) > 500 else report)
    print("-" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断] 用户中断程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n[错误] 程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

