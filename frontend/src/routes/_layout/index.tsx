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
  Loader2,
  Activity,
  Download,
  Database,
  Tag,
  Calendar,
  Layers,
  HardDrive,
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

async function runTask() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/run-task/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to run task");
  }
  return response.json();
}

async function updateData() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/update-data/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update data");
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
  net_return: number;
  net_return_pct: string;
  annualized_return: number;
  annualized_return_pct: string;
  cagr: number;
  cagr_pct: string;
  net_cagr: number;
  net_cagr_pct: string;
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

interface DataInfoSummary {
  data_range_start?: string;
  data_range_end?: string;
  trading_days: number;
  instruments_count: number;
  features_count: number;
  feature_names: string[];
  label_expression: string;
  label_description: string;
  last_update_time?: string;
}

interface RebalanceInfo {
  rebalance_period_days: number;
  is_rebalance_day: boolean;
  next_rebalance_date?: string;
  days_until_rebalance: number;
}

interface SystemSummary {
  is_initialized: boolean;
  signal_count: number;
  last_routine_time?: string;
  data_range_start?: string;
  data_range_end?: string;
  rebalance?: RebalanceInfo;
}

interface TargetPositionItem {
  rank: number;
  instrument: string;
  name: string;
  type: string;
  weight: number;
  target_value: number;
  target_shares: number;
  action: string;
}

interface AlertItem {
  level: string;
  message: string;
  action?: string;
}

interface DashboardData {
  success: boolean;
  data_info: DataInfoSummary;
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
  const [taskStatus, setTaskStatus] = useState<string>("");

  const {
    data: dashboardData,
    isLoading,
    refetch,
  } = useQuery<DashboardData>({
    queryKey: ["dashboardSummary"],
    queryFn: fetchDashboardSummary,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const taskMutation = useMutation({
    mutationFn: runTask,
  });

  const updateDataMutation = useMutation({
    mutationFn: updateData,
  });

  const backtestMutation = useMutation({
    mutationFn: runBacktest,
  });

  const handleRunTask = async () => {
    try {
      setTaskStatus("Running signal generation...");
      await taskMutation.mutateAsync();
      setTaskStatus("Signal generation completed!");
      refetch();
      // Clear status after 3 seconds
      setTimeout(() => setTaskStatus(""), 3000);
    } catch (error) {
      setTaskStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
      // Clear error after 5 seconds
      setTimeout(() => setTaskStatus(""), 5000);
    }
  };

  const handleUpdateData = async () => {
    try {
      setTaskStatus("Updating data...");
      await updateDataMutation.mutateAsync();
      setTaskStatus("Data update completed!");
      refetch();
      // Clear status after 3 seconds
      setTimeout(() => setTaskStatus(""), 3000);
    } catch (error) {
      setTaskStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
      // Clear error after 5 seconds
      setTimeout(() => setTaskStatus(""), 5000);
    }
  };

  const handleRunBacktest = async () => {
    try {
      setTaskStatus("Running backtest...");
      await backtestMutation.mutateAsync();
      setTaskStatus("Backtest completed!");
      refetch();
      // Clear status after 3 seconds
      setTimeout(() => setTaskStatus(""), 3000);
    } catch (error) {
      setTaskStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
      // Clear error after 5 seconds
      setTimeout(() => setTaskStatus(""), 5000);
    }
  };

  const isTaskRunning = taskMutation.isPending;
  const isUpdatingData = updateDataMutation.isPending;
  const isBacktestRunning = backtestMutation.isPending;

  const dataInfo = dashboardData?.data_info;
  const backtest = dashboardData?.backtest;
  const model = dashboardData?.model;
  const system = dashboardData?.system;
  const targetPositions = dashboardData?.target_positions || [];
  const alerts = dashboardData?.alerts || [];

  // Data for dashboard display
  const totalReturn = backtest?.total_return || 0;

  return (
    <div className="container mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <Badge
              variant={system?.is_initialized ? "default" : "secondary"}
              className="text-xs"
            >
              {system?.is_initialized ? "Online" : "Offline"}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            Quantitative Investment Platform Overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          {taskStatus && (
            <span
              className={`text-sm ${taskStatus.startsWith("Error") ? "text-red-600" : taskStatus.includes("completed") ? "text-green-600" : "text-blue-600"}`}
            >
              {taskStatus}
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleUpdateData}
            disabled={isUpdatingData}
          >
            {isUpdatingData ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Update Data
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRunBacktest}
            disabled={isBacktestRunning}
          >
            {isBacktestRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <BarChart3 className="h-4 w-4 mr-2" />
            )}
            Run Backtest
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleRunTask}
            disabled={isTaskRunning}
          >
            {isTaskRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Zap className="h-4 w-4 mr-2" />
            )}
            Update Portfolio
          </Button>
        </div>
      </div>

      {/* Row 0: Data & Factor Info */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Data Range Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Data Range</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-lg font-bold">
                  {dataInfo?.data_range_start && dataInfo?.data_range_end
                    ? `${dataInfo.data_range_start} ~ ${dataInfo.data_range_end}`
                    : "N/A"}
                </div>
                <p className="text-xs text-muted-foreground">
                  Trading Days: {dataInfo?.trading_days || 0}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Instruments Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Instruments</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {dataInfo?.instruments_count || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Stocks in dataset
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Fields Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fields</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {dataInfo?.fields_count || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  {dataInfo?.field_names?.join(", ") || "Raw data columns"}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Features Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Features</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {dataInfo?.features_count || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  {(() => {
                    const names = dataInfo?.feature_names || [];
                    const alphaEntry = names.find((n) => n.startsWith("+ "));
                    const regularNames = names.filter(
                      (n) => !n.startsWith("+ "),
                    );
                    const parts: string[] = [];
                    if (regularNames.length > 0) {
                      parts.push(`${regularNames.length} factors`);
                    }
                    if (alphaEntry) {
                      parts.push(alphaEntry);
                    }
                    return parts.join(", ") || "Model input features";
                  })()}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Label Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Label (Target)
            </CardTitle>
            <Tag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div
                  className="text-sm font-mono font-bold break-all"
                  title={dataInfo?.label_expression || ""}
                >
                  {dataInfo?.label_expression || "N/A"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {dataInfo?.label_description || ""}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Signal Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Signals</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {formatNumber(system?.signal_count || 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {system?.last_routine_time
                    ? `Last: ${system.last_routine_time}`
                    : "No signals generated yet"}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* KPI Cards - Row 1: Backtest Results */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Backtest Net Return Card - actual investor return after costs */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Backtest Net Return
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div
                  className={`text-2xl font-bold ${(backtest?.net_return || 0) >= 0 ? "text-green-600" : "text-red-600"}`}
                >
                  {backtest?.net_return_pct || "N/A"}
                </div>
                <p className="text-xs text-muted-foreground">
                  CAGR: {backtest?.net_cagr_pct || "N/A"}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Max Drawdown Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Backtest Max Drawdown
            </CardTitle>
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
            <CardTitle className="text-sm font-medium">
              Backtest Sharpe Ratio
            </CardTitle>
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

        {/* Backtest Info Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Backtest Info</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-sm font-medium">
                  {backtest?.backtest_date
                    ? `Date: ${backtest.backtest_date}`
                    : "No backtest yet"}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {system?.rebalance
                    ? `Rebalance: every ${system.rebalance.rebalance_period_days} days`
                    : ""}
                  {system?.rebalance?.next_rebalance_date
                    ? ` | Next: ${system.rebalance.next_rebalance_date}`
                    : ""}
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
                  <p className="text-xs">Run Task to generate</p>
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
                {/* Show top 6 holdings by weight (filter holdings, sort by weight desc, take 6) */}
                {targetPositions
                  .filter((pos) => pos.target_shares > 0)
                  .sort((a, b) => b.weight - a.weight)
                  .slice(0, 6)
                  .map((pos) => (
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
                      <span className="text-sm text-muted-foreground flex-shrink-0">
                        {pos.weight.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                {targetPositions.filter((pos) => pos.target_shares > 0).length >
                  6 && (
                  <Link to="/target-portfolio">
                    <Button variant="link" size="sm" className="w-full">
                      View all{" "}
                      {
                        targetPositions.filter((pos) => pos.target_shares > 0)
                          .length
                      }{" "}
                      positions
                    </Button>
                  </Link>
                )}
              </div>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No target portfolio yet</p>
                  <p className="text-xs">Run Task to generate</p>
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
