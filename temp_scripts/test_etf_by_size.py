#!/usr/bin/env python3
"""
测试基于规模的ETF股票池选择
使用Tushare的etf_basic和etf_share_size接口
"""


def test_tushare_api_directly():
    """直接测试Tushare API"""
    print("🔍 测试1: 直接测试Tushare API")
    print("=" * 30)

    try:
        import tushare as ts
        from pathlib import Path
        from datetime import datetime, timedelta

        # 读取token
        token_file = Path.home() / ".tushare_token"
        if not token_file.exists():
            print("❌ Tushare token文件不存在")
            return False

        with open(token_file, "r") as f:
            token = f.read().strip()

        pro = ts.pro_api(token)
        print("✅ Tushare API连接成功")

        # 测试etf_basic接口
        print("\n📊 测试etf_basic接口...")
        etf_basic = pro.etf_basic(
            list_status="L",
            fields="ts_code,extname,index_code,index_name,exchange,mgr_name",
        )
        print(f"✅ etf_basic返回{len(etf_basic)}只上市ETF")
        if len(etf_basic) > 0:
            print(
                f"   示例: {etf_basic.head(3)[['ts_code', 'extname']].to_string(index=False)}"
            )

        # 测试etf_share_size接口
        print("\n📊 测试etf_share_size接口...")
        etf_sizes = None
        for days_ago in range(1, 15):
            trade_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
            try:
                etf_sizes = pro.etf_share_size(
                    trade_date=trade_date,
                    fields="ts_code,etf_name,total_share,total_size",
                )
                if etf_sizes is not None and not etf_sizes.empty:
                    print(
                        f"✅ etf_share_size返回{len(etf_sizes)}条记录 (日期: {trade_date})"
                    )
                    # 显示前5只最大的ETF
                    top5 = etf_sizes.nlargest(5, "total_size")
                    print("   规模最大的5只ETF:")
                    for _, row in top5.iterrows():
                        size_yi = row["total_size"] / 10000  # 万元转亿元
                        print(
                            f"   - {row['ts_code']}: {row['etf_name'][:15]} - {size_yi:.1f}亿元"
                        )
                    break
            except Exception as e:
                continue

        if etf_sizes is None or etf_sizes.empty:
            print("❌ etf_share_size未返回数据")
            return False

        return True

    except Exception as e:
        print(f"❌ Tushare API测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_etf_by_size():
    """测试按规模选择ETF"""
    print("\n🚀 测试2: 通过IndexComponentsService获取ETF")
    print("=" * 45)

    try:
        from app.services.index_components_service import get_index_components_service

        service = get_index_components_service()

        # 清除缓存确保获取最新数据
        service.cache.clear()

        print("📊 开始获取ETF股票池（按规模排序）...")

        import time

        start_time = time.time()

        components = service.get_components("etf_universe", use_cache=False)

        elapsed_time = time.time() - start_time
        print(f"⏱️  获取耗时: {elapsed_time:.1f}秒")

        print(f"✅ 成功获取{len(components)}只ETF")

        if len(components) == 0:
            print("❌ 未获取到任何ETF")
            return False

        # 显示前20只ETF
        print(f"\n📋 前20只ETF（按规模排序）:")
        for i, etf_code in enumerate(components[:20]):
            print(f"   {i+1:2d}. {etf_code}")

        # 验证格式
        valid_count = 0
        for code in components:
            if code.startswith(("SH", "SZ")) and len(code) == 8:
                valid_count += 1

        print(f"\n✅ 格式验证: {valid_count}/{len(components)} 符合Qlib格式")

        if len(components) >= 50:
            print("🎉 ETF股票池获取成功！")
            return True
        else:
            print("⚠️  ETF数量较少，可能需要检查数据源")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_config_parameters():
    """测试配置参数"""
    print(f"\n🔍 测试3: 配置参数")
    print("=" * 20)

    try:
        import yaml
        from pathlib import Path

        config_path = Path("/app/app/config/index_config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        etf_config = config["indexes"]["etf_universe"]

        print("📋 ETF Universe配置:")
        print(f"   - 名称: {etf_config['name']}")
        print(f"   - 数据源: {etf_config['components_source']}")
        print(f"   - 选择数量: {etf_config['top_n_etfs']}只")
        print(f"   - 基准: {etf_config['benchmark_code']}")

        return True

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def main():
    """主函数"""
    print("⚡ ETF规模筛选测试 (基于Tushare etf_basic + etf_share_size)")
    print("=" * 55)

    tests = [
        ("Tushare API直接测试", test_tushare_api_directly),
        ("IndexComponentsService测试", test_etf_by_size),
        ("配置参数", test_config_parameters),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))

    # 总结
    print(f"\n" + "=" * 55)
    print("📊 测试结果")
    print("=" * 55)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n🎯 通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   - {test_name}: {status}")

    if passed == total:
        print(f"\n🎉 所有测试通过！ETF股票池功能正常")
        print("💡 使用的Tushare接口:")
        print("   - etf_basic: 获取ETF基本信息")
        print("   - etf_share_size: 获取ETF规模数据 (total_size)")
    else:
        print(f"\n⚠️  存在问题需要解决")


if __name__ == "__main__":
    main()
