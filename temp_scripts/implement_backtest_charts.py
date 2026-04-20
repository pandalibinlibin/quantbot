#!/usr/bin/env python3
"""
实现Enhanced Indexing Strategy回测图表可视化
基于现有的良好图表数据基础，实现前端图表组件
"""

import requests
import json
import time


def test_current_chart_data_structure():
    """测试当前图表数据结构"""
    print("🔍 分析当前图表数据结构...")

    try:
        # 执行回测获取最新图表数据
        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json={"benchmark": "SH000300"},
            timeout=300,
        )

        if response.status_code == 200:
            result = response.json()

            if result.get("status") == "success":
                charts = result.get("charts", {})

                print(f"   ✅ 获取到 {len(charts)} 个图表数据")

                # 详细分析每个图表的数据结构
                for chart_name, chart_data in charts.items():
                    print(f"\n   📊 {chart_name}:")

                    if isinstance(chart_data, list):
                        print(f"      • 数据类型: List")
                        print(f"      • 数据点数: {len(chart_data)}")

                        if len(chart_data) > 0:
                            sample = chart_data[0]
                            if isinstance(sample, dict):
                                print(f"      • 字段: {list(sample.keys())}")
                            else:
                                print(f"      • 元素类型: {type(sample).__name__}")

                    elif isinstance(chart_data, dict):
                        print(f"      • 数据类型: Dict")
                        print(f"      • 字段数: {len(chart_data)}")

                        for key, value in chart_data.items():
                            if isinstance(value, list):
                                print(f"        - {key}: List[{len(value)}]")
                            else:
                                print(
                                    f"        - {key}: {type(value).__name__} = {value}"
                                )
                    else:
                        print(f"      • 数据类型: {type(chart_data).__name__}")

                return charts
            else:
                print(f"   ❌ 回测失败: {result.get('error', 'Unknown')}")
                return None
        else:
            print(f"   ❌ API调用失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ 数据分析异常: {e}")
        return None


def generate_frontend_chart_components():
    """生成前端图表组件代码"""
    print("\n🎨 生成前端图表组件代码...")

    # 基于现有数据结构设计组件
    components = {
        "EquityCurveChart": {
            "description": "净值曲线图表 - 基于cumulative_returns数据",
            "data_source": "result.charts.cumulative_returns",
            "chart_type": "LineChart",
            "code_template": """
// 净值曲线图表组件
function EquityCurveChart({ data }: { data: any[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>净值曲线</CardTitle>
        <CardDescription>策略累积收益表现</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="cumulative_return" 
              stroke="#8884d8" 
              name="策略收益"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}""",
        },
        "DrawdownChart": {
            "description": "回撤分析图表 - 基于max_drawdown_info数据",
            "data_source": "result.charts.max_drawdown_info",
            "chart_type": "AreaChart",
            "code_template": """
// 回撤分析图表组件
function DrawdownChart({ data }: { data: any }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>回撤分析</CardTitle>
        <CardDescription>
          最大回撤: {(data.max_drawdown * 100).toFixed(2)}% 
          (发生于 {data.max_drawdown_date})
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>峰值日期</Label>
              <div className="font-mono text-sm">{data.peak_date}</div>
            </div>
            <div>
              <Label>谷底日期</Label>
              <div className="font-mono text-sm">{data.trough_date}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>回撤天数</Label>
              <div className="font-mono text-sm">{data.drawdown_days} 天</div>
            </div>
            <div>
              <Label>恢复日期</Label>
              <div className="font-mono text-sm">{data.recovery_date || '未恢复'}</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}""",
        },
        "ReturnDistributionChart": {
            "description": "收益分布图表 - 基于return_distribution数据",
            "data_source": "result.charts.return_distribution",
            "chart_type": "BarChart",
            "code_template": """
// 收益分布图表组件
function ReturnDistributionChart({ data }: { data: any[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>收益分布</CardTitle>
        <CardDescription>日收益率分布统计</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="range" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#82ca9d" name="频次" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}""",
        },
        "DailyReturnsChart": {
            "description": "日收益率图表 - 基于daily_returns数据",
            "data_source": "result.charts.daily_returns",
            "chart_type": "LineChart",
            "code_template": """
// 日收益率图表组件
function DailyReturnsChart({ data }: { data: any[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>日收益率</CardTitle>
        <CardDescription>每日收益率波动情况</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line 
              type="monotone" 
              dataKey="return" 
              stroke="#ff7300" 
              name="日收益率"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}""",
        },
    }

    print("   📋 设计的前端图表组件:")
    for comp_name, comp_info in components.items():
        print(f"      • {comp_name}")
        print(f"        描述: {comp_info['description']}")
        print(f"        数据源: {comp_info['data_source']}")
        print(f"        图表类型: {comp_info['chart_type']}")
        print()

    return components


def suggest_backtest_page_enhancement():
    """建议回测页面增强方案"""
    print("💡 回测页面增强实施方案:")

    enhancement_plan = {
        "file_to_modify": "frontend/src/routes/_layout/backtest.tsx",
        "modifications": [
            {
                "section": "导入部分",
                "action": "添加Recharts组件导入",
                "code": """
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer
} from 'recharts';""",
            },
            {
                "section": "结果显示部分",
                "action": "在现有结果卡片后添加图表组件",
                "location": "第426行 backtestResult 显示区域后",
                "code": """
{/* 图表可视化区域 */}
{backtestResult?.charts && (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    {/* 净值曲线图表 */}
    {backtestResult.charts.cumulative_returns && (
      <EquityCurveChart data={backtestResult.charts.cumulative_returns} />
    )}
    
    {/* 回撤分析图表 */}
    {backtestResult.charts.max_drawdown_info && (
      <DrawdownChart data={backtestResult.charts.max_drawdown_info} />
    )}
    
    {/* 收益分布图表 */}
    {backtestResult.charts.return_distribution && (
      <ReturnDistributionChart data={backtestResult.charts.return_distribution} />
    )}
    
    {/* 日收益率图表 */}
    {backtestResult.charts.daily_returns && (
      <DailyReturnsChart data={backtestResult.charts.daily_returns} />
    )}
  </div>
)}""",
            },
        ],
        "dependencies": ["recharts - 已安装的图表库", "现有的Card、CardHeader等UI组件"],
    }

    print(f"   📁 修改文件: {enhancement_plan['file_to_modify']}")
    print(f"   🔧 修改内容:")

    for i, mod in enumerate(enhancement_plan["modifications"], 1):
        print(f"      {i}. {mod['section']}")
        print(f"         操作: {mod['action']}")
        if "location" in mod:
            print(f"         位置: {mod['location']}")
        print()

    print(f"   📦 依赖项: {', '.join(enhancement_plan['dependencies'])}")

    return enhancement_plan


def main():
    """主实施流程"""
    print("🎨 Enhanced Indexing Strategy 回测图表可视化实现")
    print("=" * 60)

    # 1. 分析当前图表数据结构
    current_charts = test_current_chart_data_structure()

    if not current_charts:
        print("\n❌ 无法获取图表数据，需要先修复回测功能")
        return

    # 2. 生成前端组件代码
    components = generate_frontend_chart_components()

    # 3. 建议页面增强方案
    enhancement_plan = suggest_backtest_page_enhancement()

    print("\n" + "=" * 60)
    print("🎉 回测图表可视化实现方案完成")

    print("\n📊 现有数据优势:")
    print("   ✅ cumulative_returns: 完整净值数据")
    print("   ✅ max_drawdown_info: 详细回撤信息")
    print("   ✅ return_distribution: 收益分布统计")
    print("   ✅ daily_returns: 日收益率数据")

    print("\n🚀 实施建议:")
    print("   1. 基于现有数据结构实现前端图表组件")
    print("   2. 使用Recharts库创建专业图表")
    print("   3. 采用2x2网格布局展示4个核心图表")
    print("   4. 添加图表交互功能（缩放、筛选等）")

    print("\n📋 下一步行动:")
    print("   1. 修改 frontend/src/routes/_layout/backtest.tsx")
    print("   2. 添加图表组件代码")
    print("   3. 测试图表显示效果")
    print("   4. 优化图表样式和交互")


if __name__ == "__main__":
    main()
