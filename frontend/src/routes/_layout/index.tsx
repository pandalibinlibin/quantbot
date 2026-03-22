import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import {
  TrendingDown,
  Target,
  AlertTriangle,
  CheckCircle2,
  Info,
  BarChart3,
  Zap,
  Play,
  Loader2,
  Activity,
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

async function runRoutine() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/online/routine`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to run routine");
  }
  return response.json();
}

async function runBacktest() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/backtest/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to run backtest");
  }
  return response.json();
}

// Types
interface BacktestSummary {
  has_results: boolean;
  total_return: number;
  total_return_pct: string;
  annualized_return: number;
  annualized_return_pct: string;
  max_drawdown: number;
  max_drawdown_pct: string;
  sharpe_ratio: number;
  trading_days: number;
  backtest_date?: string;
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

interface TargetPositionItem {
  rank: number;
  instrument: string;
  name: string;
  type: string;
  weight: number;
  target_value: number;
  action: string;
}

interface AlertItem {
  level: string;
  message: string;
  action?: string;
}

interface DashboardData {
  success: boolean;
  backtest: BacktestSummary;
  model: ModelSummary;
  system: SystemSummary;
  target_positions: TargetPositionItem[];
  alerts: AlertItem[];
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
  const [dailyTaskStatus, setDailyTaskStatus] = useState<string>("");

  const {
    data: dashboardData,
    isLoading,
    refetch,
  } = useQuery<DashboardData>({
    queryKey: ["dashboardSummary"],
    queryFn: fetchDashboardSummary,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const routineMutation = useMutation({
    mutationFn: runRoutine,
  });

  const backtestMutation = useMutation({
    mutationFn: runBacktest,
  });

  const handleDailyTask = async () => {
    try {
      // Step 1: Run Routine
      setDailyTaskStatus("Running routine...");
      await routineMutation.mutateAsync();

      // Step 2: Run Backtest
      setDailyTaskStatus("Running backtest...");
      await backtestMutation.mutateAsync();

      // Done
      setDailyTaskStatus("Daily task completed!");
      refetch();

      // Clear status after 3 seconds
      setTimeout(() => setDailyTaskStatus(""), 3000);
    } catch (error) {
      setDailyTaskStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
      // Clear error after 5 seconds
      setTimeout(() => setDailyTaskStatus(""), 5000);
    }
  };

  const isDailyTaskRunning =
    routineMutation.isPending || backtestMutation.isPending;

  const backtest = dashboardData?.backtest;
  const model = dashboardData?.model;
  const system = dashboardData?.system;
  const targetPositions = dashboardData?.target_positions || [];
  const alerts = dashboardData?.alerts || [];

  // Calculate return color
  const totalReturn = backtest?.total_return || 0;
  const isPositive = totalReturn >= 0;

  return (
    <div className="container mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            ETF Enhanced Indexing Strategy Overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          {dailyTaskStatus && (
            <span
              className={`text-sm ${dailyTaskStatus.startsWith("Error") ? "text-red-600" : dailyTaskStatus.includes("completed") ? "text-green-600" : "text-blue-600"}`}
            >
              {dailyTaskStatus}
            </span>
          )}
          <Button
            variant="default"
            size="sm"
            onClick={handleDailyTask}
            disabled={isDailyTaskRunning}
          >
            {isDailyTaskRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Daily Task
          </Button>
        </div>
      </div>

      {/* KPI Cards - Row 1: Backtest Results */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Return Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Return</CardTitle>
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
                  {backtest?.total_return_pct || "N/A"}
                </div>
                <p className="text-xs text-muted-foreground">
                  Ann: {backtest?.annualized_return_pct || "N/A"}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Max Drawdown Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold text-red-600">
                  {backtest?.max_drawdown_pct || "N/A"}
                </div>
                <p className="text-xs text-muted-foreground">
                  Trading Days: {backtest?.trading_days || 0}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Sharpe Ratio Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div
                  className={`text-2xl font-bold ${(backtest?.sharpe_ratio || 0) >= 1 ? "text-green-600" : (backtest?.sharpe_ratio || 0) >= 0 ? "text-yellow-600" : "text-red-600"}`}
                >
                  {backtest?.sharpe_ratio?.toFixed(2) || "N/A"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {(backtest?.sharpe_ratio || 0) >= 2
                    ? "Excellent"
                    : (backtest?.sharpe_ratio || 0) >= 1
                      ? "Good"
                      : (backtest?.sharpe_ratio || 0) >= 0
                        ? "Fair"
                        : "Poor"}
                </p>
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

      {/* Row 2: Model Metrics & Target Portfolio */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Model Metrics Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Model Performance
            </CardTitle>
            <CardDescription>Prediction model quality metrics</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-[180px] bg-muted animate-pulse rounded" />
            ) : model?.has_metrics ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-muted/50 rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">IC (Mean)</p>
                    <p className="text-2xl font-bold">
                      {model.ic?.toFixed(4) || "N/A"}
                    </p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">ICIR</p>
                    <p className="text-2xl font-bold">
                      {model.icir?.toFixed(2) || "N/A"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Model Evaluation
                  </span>
                  <Badge
                    variant={
                      model.evaluation === "Excellent" ||
                      model.evaluation === "Good"
                        ? "default"
                        : "secondary"
                    }
                  >
                    {model.evaluation}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  IC {">"} 0.03 is good, IC {">"} 0.05 is excellent
                </p>
              </div>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Target className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No model metrics yet</p>
                  <p className="text-xs">Run Daily Task to generate</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Target Portfolio Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Target Portfolio
            </CardTitle>
            <CardDescription>Top positions from latest signal</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-8 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : targetPositions.length > 0 ? (
              <div className="space-y-2">
                {targetPositions.slice(0, 6).map((pos) => (
                  <div
                    key={pos.instrument}
                    className="flex items-center justify-between py-1"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-xs text-muted-foreground w-4 flex-shrink-0">
                        {pos.rank}
                      </span>
                      <Badge
                        variant={pos.type === "etf" ? "default" : "outline"}
                        className="text-xs flex-shrink-0"
                      >
                        {pos.type === "etf" ? "ETF" : "Alpha"}
                      </Badge>
                      <div className="min-w-0 flex-1">
                        <span className="font-medium text-sm">
                          {pos.instrument}
                        </span>
                        {pos.name && (
                          <span className="text-xs text-muted-foreground ml-1 truncate">
                            {pos.name}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-sm text-muted-foreground">
                        {pos.weight.toFixed(1)}%
                      </span>
                      <Badge
                        variant={
                          pos.action === "buy"
                            ? "default"
                            : pos.action === "sell"
                              ? "destructive"
                              : "secondary"
                        }
                        className="text-xs w-12 justify-center"
                      >
                        {pos.action}
                      </Badge>
                    </div>
                  </div>
                ))}
                {targetPositions.length > 6 && (
                  <Link to="/target-portfolio">
                    <Button variant="link" size="sm" className="w-full">
                      View all {targetPositions.length} positions
                    </Button>
                  </Link>
                )}
              </div>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No target portfolio yet</p>
                  <p className="text-xs">Run Daily Task to generate</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Alerts */}
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
            <div className="grid gap-3 md:grid-cols-2">
              {alerts.map((alert, index) => (
                <div
                  key={index}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
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
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <div className="text-center">
                <CheckCircle2 className="h-12 w-12 mx-auto mb-2 opacity-50 text-green-600" />
                <p>All systems operational</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
