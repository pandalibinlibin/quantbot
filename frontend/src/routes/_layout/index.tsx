import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Info,
  RefreshCw,
  ArrowRight,
  BarChart3,
  Zap,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { OpenAPI } from "@/client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - QuantBot",
      },
    ],
  }),
});

// API helper
async function fetchDashboardSummary() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/dashboard/summary`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  if (!response.ok) {
    throw new Error("Failed to fetch dashboard summary");
  }
  return response.json();
}

// Types
interface PortfolioSummary {
  total_value: number;
  initial_cash: number;
  total_return: number;
  total_return_pct: string;
  annualized_return_pct?: string;
  position_count: number;
  trading_started: boolean;
}

interface ModelSummary {
  ic?: number;
  icir?: number;
  evaluation: string;
  has_metrics: boolean;
}

interface SystemSummary {
  is_initialized: boolean;
  signal_count: number;
  last_routine_time?: string;
  data_range_start?: string;
  data_range_end?: string;
}

interface HoldingItem {
  instrument: string;
  value: number;
  weight: number;
  shares: number;
}

interface ActivityItem {
  time: string;
  type: string;
  message: string;
  success: boolean;
}

interface AlertItem {
  level: string;
  message: string;
  action?: string;
}

interface DashboardData {
  success: boolean;
  portfolio: PortfolioSummary;
  model: ModelSummary;
  system: SystemSummary;
  top_holdings: HoldingItem[];
  recent_activities: ActivityItem[];
  alerts: AlertItem[];
}

// Format currency - always show full number
function formatCurrency(value: number): string {
  return `¥${value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Format number with K/M suffix
function formatNumber(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toString();
}

function Dashboard() {
  const {
    data: dashboardData,
    isLoading,
    refetch,
    isRefetching,
  } = useQuery<DashboardData>({
    queryKey: ["dashboardSummary"],
    queryFn: fetchDashboardSummary,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const portfolio = dashboardData?.portfolio;
  const model = dashboardData?.model;
  const system = dashboardData?.system;
  const topHoldings = dashboardData?.top_holdings || [];
  const recentActivities = dashboardData?.recent_activities || [];
  const alerts = dashboardData?.alerts || [];

  // Calculate return color
  const returnValue = portfolio?.total_return || 0;
  const isPositive = returnValue >= 0;

  // Mock performance data for chart (in real implementation, fetch from API)
  const performanceData = [
    { date: "Day 1", return: 0 },
    { date: "Day 2", return: returnValue > 0 ? returnValue * 0.3 : 0 },
    { date: "Day 3", return: returnValue > 0 ? returnValue * 0.5 : 0 },
    { date: "Day 4", return: returnValue > 0 ? returnValue * 0.7 : 0 },
    { date: "Today", return: returnValue },
  ];

  return (
    <div className="container mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            System overview and key metrics
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isRefetching}
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${isRefetching ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Portfolio Value Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Portfolio Value
            </CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {formatCurrency(portfolio?.total_value || 0)}
                </div>
                <div
                  className={`flex items-center text-xs ${isPositive ? "text-green-600" : "text-red-600"}`}
                >
                  {isPositive ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  )}
                  {isPositive ? "+" : ""}
                  {formatCurrency(returnValue)}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Return Rate Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Return Rate</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div
                  className={`text-2xl font-bold ${isPositive ? "text-green-600" : "text-red-600"}`}
                >
                  {portfolio?.total_return_pct || "0.00%"}
                </div>
                <p className="text-xs text-muted-foreground">
                  Ann: {portfolio?.annualized_return_pct || "N/A"}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Model IC Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Model IC</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {model?.ic !== undefined && model?.ic !== null
                    ? model.ic.toFixed(4)
                    : "N/A"}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    ICIR: {model?.icir?.toFixed(2) || "N/A"}
                  </span>
                  {model?.has_metrics && (
                    <Badge
                      variant={
                        model.evaluation === "Excellent" ||
                        model.evaluation === "Good"
                          ? "default"
                          : "secondary"
                      }
                      className="text-xs"
                    >
                      {model.evaluation}
                    </Badge>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* System Status Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Status</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={system?.is_initialized ? "default" : "secondary"}
                  >
                    {system?.is_initialized ? "Online" : "Offline"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Signals: {formatNumber(system?.signal_count || 0)}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Middle Row: Chart and Top Holdings */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Portfolio Performance Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Portfolio Performance
            </CardTitle>
            <CardDescription>Cumulative return over time</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-[200px] bg-muted animate-pulse rounded" />
            ) : portfolio?.trading_started ? (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={performanceData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="stroke-muted"
                    />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      className="text-muted-foreground"
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) => formatCurrency(v)}
                      className="text-muted-foreground"
                    />
                    <Tooltip
                      formatter={(value) => [
                        formatCurrency(Number(value) || 0),
                        "Return",
                      ]}
                    />
                    <ReferenceLine y={0} stroke="#888" strokeDasharray="3 3" />
                    <Line
                      type="monotone"
                      dataKey="return"
                      stroke={isPositive ? "#22c55e" : "#ef4444"}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No trading data yet</p>
                  <Link to="/paper-trading">
                    <Button variant="link" size="sm">
                      Start Paper Trading{" "}
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Holdings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5" />
              Top Holdings
            </CardTitle>
            <CardDescription>Your largest positions by value</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-8 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : topHoldings.length > 0 ? (
              <div className="space-y-3">
                {topHoldings.map((holding, index) => (
                  <div
                    key={holding.instrument}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-muted-foreground w-5">
                        {index + 1}.
                      </span>
                      <span className="font-medium">{holding.instrument}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {formatCurrency(holding.value)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {holding.weight.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Wallet className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No holdings yet</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom Row: Recent Activity and Alerts */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>Latest system events</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-8 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : recentActivities.length > 0 ? (
              <div className="space-y-3">
                {recentActivities.map((activity, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <CheckCircle2
                      className={`h-4 w-4 mt-0.5 ${activity.success ? "text-green-600" : "text-red-600"}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{activity.message}</p>
                      <p className="text-xs text-muted-foreground">
                        {activity.time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[120px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No recent activity</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Alerts & Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Alerts & Actions
            </CardTitle>
            <CardDescription>Items requiring your attention</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="h-8 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.map((alert, index) => (
                  <div
                    key={index}
                    className={`flex items-start gap-3 p-2 rounded-lg ${
                      alert.level === "error"
                        ? "bg-red-50 dark:bg-red-950"
                        : alert.level === "warning"
                          ? "bg-yellow-50 dark:bg-yellow-950"
                          : "bg-blue-50 dark:bg-blue-950"
                    }`}
                  >
                    {alert.level === "error" ? (
                      <AlertTriangle className="h-4 w-4 mt-0.5 text-red-600" />
                    ) : alert.level === "warning" ? (
                      <AlertTriangle className="h-4 w-4 mt-0.5 text-yellow-600" />
                    ) : (
                      <Info className="h-4 w-4 mt-0.5 text-blue-600" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{alert.message}</p>
                      {alert.action === "run_routine" && (
                        <Link to="/routine">
                          <Button variant="link" size="sm" className="h-6 px-0">
                            Go to Routine{" "}
                            <ArrowRight className="h-3 w-3 ml-1" />
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[120px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <CheckCircle2 className="h-12 w-12 mx-auto mb-2 opacity-50 text-green-600" />
                  <p>All systems operational</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
