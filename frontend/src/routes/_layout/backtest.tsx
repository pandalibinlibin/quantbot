import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  TrendingUp,
  TrendingDown,
  Settings,
  Calendar,
  DollarSign,
  Percent,
  BarChart3,
  Activity,
  Target,
  AlertTriangle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";
import { OpenAPI } from "@/client";
import { toast } from "sonner";

// Info tooltip component for metric explanations
function MetricTooltip({ content }: { content: string }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help ml-1" />
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[250px]">
          <p className="text-xs">{content}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Temporary helper to fetch backtest config until API client is regenerated
async function fetchBacktestConfig() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/backtest/config`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  if (!response.ok) {
    throw new Error("Failed to fetch backtest config");
  }
  return response.json();
}

// Temporary helper to fetch latest backtest result
async function fetchLatestBacktestResult() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/backtest/latest-result`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    },
  );
  if (!response.ok) {
    throw new Error("Failed to fetch latest backtest result");
  }
  return response.json();
}

// Temporary helper to fetch backtest status
async function fetchBacktestStatus() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/backtest/status`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  if (!response.ok) {
    throw new Error("Failed to fetch backtest status");
  }
  return response.json();
}

// Temporary helper to execute backtest
async function executeBacktest() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/backtest/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      benchmark: "SH000300", // Use the correct benchmark format that works
    }),
  });
  if (!response.ok) {
    throw new Error("Failed to execute backtest");
  }
  return response.json();
}

export const Route = createFileRoute("/_layout/backtest")({
  component: BacktestPage,
  head: () => ({ meta: [{ title: "Backtest - Qlib Quantbot" }] }),
});

// Helper function to format currency
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

// Helper function to format percentage
function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function BacktestPage() {
  const queryClient = useQueryClient();

  // Query for backtest configuration
  const { data: configData, isLoading: configLoading } = useQuery({
    queryKey: ["backtestConfig"],
    queryFn: () => fetchBacktestConfig(),
  });

  // Query for backtest status
  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ["backtestStatus"],
    queryFn: () => fetchBacktestStatus(),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Query for latest backtest result (persisted across page navigation)
  const { data: latestResultData } = useQuery({
    queryKey: ["latestBacktestResult"],
    queryFn: () => fetchLatestBacktestResult(),
  });

  // Mutation for running backtest
  const runBacktestMutation = useMutation({
    mutationFn: () => executeBacktest(),
    onSuccess: (response: any) => {
      if (response.status === "success") {
        toast.success(
          `Backtest completed! Net return: ${formatPercent(response.net_return || 0)}`,
        );
      } else {
        toast.error(`Backtest failed: ${response.error || response.message}`);
      }
      // Refresh status and latest result after backtest
      queryClient.invalidateQueries({ queryKey: ["backtestStatus"] });
      queryClient.invalidateQueries({ queryKey: ["latestBacktestResult"] });
    },
    onError: (error) => {
      toast.error(`Backtest failed: ${error.message}`);
    },
  });

  // Extract config
  const config = configData?.config;
  const strategyConfig = config?.strategy;
  const backtestConfig = config?.backtest;
  const exchangeKwargs = backtestConfig?.exchange_kwargs || {};

  // Extract status
  const status = statusData;

  // Get backtest result - prefer mutation data, fallback to cached result
  const backtestResult =
    runBacktestMutation.data ||
    (latestResultData?.status === "success" ? latestResultData.result : null);

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Backtest</h1>
              <p className="text-muted-foreground">
                Evaluate strategy performance using historical data
              </p>
            </div>
            <Button
              size="lg"
              onClick={() => runBacktestMutation.mutate()}
              disabled={runBacktestMutation.isPending || !status?.ready}
              className="px-8"
            >
              {runBacktestMutation.isPending ? (
                <>
                  <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-5 w-5" />
                  Run Backtest
                </>
              )}
            </Button>
          </div>

          {/* Strategy Configuration Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-blue-500" />
                <CardTitle className="text-lg">
                  Strategy Configuration
                </CardTitle>
              </div>
              <CardDescription>
                Configuration from backtest_config.yaml
              </CardDescription>
            </CardHeader>
            <CardContent>
              {configLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Loading configuration...
                </div>
              ) : configData?.status === "error" ? (
                <div className="flex items-center gap-2 text-red-500">
                  <XCircle className="h-4 w-4" />
                  {configData.error || "Failed to load configuration"}
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Strategy Type */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-muted-foreground">Strategy</Label>
                      <div className="flex items-center gap-2 mt-1">
                        <TrendingUp className="h-4 w-4 text-green-500" />
                        <span className="font-medium">
                          {strategyConfig?.class || "N/A"}
                        </span>
                      </div>
                    </div>
                    <div>
                      <Label className="text-muted-foreground">
                        Module Path
                      </Label>
                      <div className="text-sm font-mono mt-1">
                        {strategyConfig?.module_path || "N/A"}
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Strategy Parameters */}
                  <div>
                    <Label className="text-muted-foreground mb-2 block">
                      Strategy Parameters
                    </Label>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-muted/50 rounded-md p-2 text-sm">
                        <span className="text-muted-foreground">account:</span>{" "}
                        <span className="font-medium">
                          {backtestConfig?.account
                            ? formatCurrency(backtestConfig.account)
                            : "N/A"}
                        </span>
                      </div>
                      <div className="bg-muted/50 rounded-md p-2 text-sm">
                        <span className="text-muted-foreground">
                          benchmark:
                        </span>{" "}
                        <span className="font-medium">
                          {backtestConfig?.benchmark || "N/A"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Exchange Parameters */}
                  <div>
                    <Label className="text-muted-foreground mb-2 block">
                      Trading Costs
                    </Label>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {Object.entries(exchangeKwargs).map(([key, value]) => (
                        <div
                          key={key}
                          className="bg-muted/50 rounded-md p-2 text-sm"
                        >
                          <span className="text-muted-foreground">{key}:</span>{" "}
                          <span className="font-medium">
                            {typeof value === "number"
                              ? value < 0.01 && value > 0
                                ? value.toFixed(4)
                                : value.toLocaleString()
                              : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Backtest Status Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <RefreshCw
                  className={`h-5 w-5 ${runBacktestMutation.isPending ? "animate-spin text-blue-500" : "text-gray-500"}`}
                />
                <CardTitle className="text-lg">Backtest Status</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Loading status...
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Ready Status */}
                  <div className="flex items-center gap-3">
                    {status?.ready ? (
                      <>
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                        <span className="text-sm">
                          Ready for backtest. Predictions available.
                        </span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-5 w-5 text-yellow-500" />
                        <span className="text-sm text-muted-foreground">
                          {status?.message || "Not ready for backtest"}
                        </span>
                      </>
                    )}
                  </div>

                  {/* Latest Model */}
                  {status?.latest_model && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span>Latest Model:</span>
                      <Badge variant="secondary">{status.latest_model}</Badge>
                    </div>
                  )}

                  {/* Mutation Status */}
                  <div className="flex items-center gap-3 pt-2">
                    {runBacktestMutation.isPending ? (
                      <>
                        <Badge variant="default" className="bg-blue-500">
                          Running
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          Backtest in progress... This may take a moment.
                        </span>
                      </>
                    ) : runBacktestMutation.isSuccess ? (
                      <>
                        <Badge
                          variant="default"
                          className={
                            backtestResult?.status === "success"
                              ? "bg-green-500"
                              : "bg-red-500"
                          }
                        >
                          {backtestResult?.status === "success"
                            ? "Completed"
                            : "Failed"}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {backtestResult?.message}
                        </span>
                      </>
                    ) : runBacktestMutation.isError ? (
                      <>
                        <Badge variant="destructive">Error</Badge>
                        <span className="text-sm text-red-500">
                          {runBacktestMutation.error?.message}
                        </span>
                      </>
                    ) : (
                      <>
                        <Badge variant="secondary">Idle</Badge>
                        <span className="text-sm text-muted-foreground">
                          Ready to run backtest
                        </span>
                      </>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Backtest Results Card - Only show when we have results */}
          {backtestResult?.status === "success" && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-purple-500" />
                  <CardTitle className="text-lg">Backtest Results</CardTitle>
                </div>
                <CardDescription>
                  Performance metrics from {backtestResult.start_time} to{" "}
                  {backtestResult.end_time}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {/* Data Time Range */}
                  <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4 md:col-span-3">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <Calendar className="h-4 w-4" />
                      <span className="text-sm">Data Time Range</span>
                    </div>
                    <div className="text-lg font-medium">
                      {backtestResult.data_start_time ||
                        backtestResult.start_time}{" "}
                      ~{" "}
                      {backtestResult.data_end_time || backtestResult.end_time}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Backtest period: {backtestResult.start_time} ~{" "}
                      {backtestResult.end_time}
                    </div>
                  </div>

                  {/* Trading Period */}
                  <div className="bg-muted/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <Calendar className="h-4 w-4" />
                      <span className="text-sm">Trading Days</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {backtestResult.trading_days}
                    </div>
                  </div>

                  {/* Total Return */}
                  <div className="bg-muted/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <Percent className="h-4 w-4" />
                      <span className="text-sm">Total Return</span>
                    </div>
                    <div
                      className={`text-2xl font-bold ${
                        (backtestResult.total_return || 0) >= 0
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {formatPercent(backtestResult.total_return || 0)}
                    </div>
                  </div>

                  {/* Net Return */}
                  <div className="bg-muted/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <TrendingUp className="h-4 w-4" />
                      <span className="text-sm">Net Return</span>
                    </div>
                    <div
                      className={`text-2xl font-bold ${
                        (backtestResult.net_return || 0) >= 0
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {formatPercent(backtestResult.net_return || 0)}
                    </div>
                  </div>

                  {/* Total Cost */}
                  <div className="bg-muted/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <DollarSign className="h-4 w-4" />
                      <span className="text-sm">Total Cost</span>
                    </div>
                    <div className="text-2xl font-bold text-orange-600">
                      {formatPercent(backtestResult.total_cost || 0)}
                    </div>
                  </div>

                  {/* Final Account */}
                  <div className="bg-muted/50 rounded-lg p-4 md:col-span-2">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <DollarSign className="h-4 w-4" />
                      <span className="text-sm">Final Account Value</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {formatCurrency(backtestResult.final_account || 0)}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Risk Metrics Card - Only show when we have risk metrics */}
          {backtestResult?.status === "success" &&
            backtestResult.risk_metrics && (
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-blue-500" />
                    <CardTitle className="text-lg">Risk Metrics</CardTitle>
                  </div>
                  <CardDescription>
                    Key risk-adjusted performance indicators
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {/* Annualized Return */}
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <TrendingUp className="h-4 w-4" />
                        <span className="text-sm ml-2">Annualized Return</span>
                        <MetricTooltip content="将投资收益换算成一年的收益率。例如3个月赚5%，年化约20%。用于比较不同时间长度的投资表现。" />
                      </div>
                      <div
                        className={`text-xl font-bold ${
                          (backtestResult.risk_metrics.annualized_return ||
                            0) >= 0
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {formatPercent(
                          backtestResult.risk_metrics.annualized_return || 0,
                        )}
                      </div>
                    </div>

                    {/* Max Drawdown */}
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <TrendingDown className="h-4 w-4" />
                        <span className="text-sm ml-2">Max Drawdown</span>
                        <MetricTooltip content="从历史最高点到最低点的最大跌幅。衡量风险的核心指标，告诉你最坏情况下可能亏多少。投资者通常无法承受超过30%的回撤。" />
                      </div>
                      <div className="text-xl font-bold text-red-600">
                        {formatPercent(
                          backtestResult.risk_metrics.max_drawdown || 0,
                        )}
                      </div>
                    </div>

                    {/* Sharpe Ratio */}
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <Target className="h-4 w-4" />
                        <span className="text-sm ml-2">Sharpe Ratio</span>
                        <MetricTooltip content="每承担1单位风险能获得多少超额收益。>1表示不错，>2表示优秀，<0表示亏损。是最重要的风险调整收益指标。" />
                      </div>
                      <div
                        className={`text-xl font-bold ${
                          (backtestResult.risk_metrics.sharpe_ratio || 0) >= 1
                            ? "text-green-600"
                            : (backtestResult.risk_metrics.sharpe_ratio || 0) >=
                                0
                              ? "text-yellow-600"
                              : "text-red-600"
                        }`}
                      >
                        {(
                          backtestResult.risk_metrics.sharpe_ratio || 0
                        ).toFixed(2)}
                      </div>
                    </div>

                    {/* Volatility */}
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <AlertTriangle className="h-4 w-4" />
                        <span className="text-sm ml-2">Volatility</span>
                        <MetricTooltip content="收益的标准差，衡量收益的波动程度。波动率越高，风险越大。稳定的策略波动率较低。" />
                      </div>
                      <div className="text-xl font-bold">
                        {formatPercent(
                          backtestResult.risk_metrics.volatility || 0,
                        )}
                      </div>
                    </div>

                    {/* Calmar Ratio */}
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <BarChart3 className="h-4 w-4" />
                        <span className="text-sm ml-2">Calmar Ratio</span>
                        <MetricTooltip content="年化收益÷最大回撤。衡量收益与风险的平衡，>1表示收益能覆盖风险，越高越好。" />
                      </div>
                      <div className="text-xl font-bold">
                        {(
                          backtestResult.risk_metrics.calmar_ratio || 0
                        ).toFixed(2)}
                      </div>
                    </div>

                    {/* Win Rate */}
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <CheckCircle2 className="h-4 w-4" />
                        <span className="text-sm ml-2">Win Rate</span>
                        <MetricTooltip content="盈利天数占总交易天数的比例。>50%表示赢的次数多于输的次数。" />
                      </div>
                      <div
                        className={`text-xl font-bold ${
                          (backtestResult.risk_metrics.win_rate || 0) >= 0.5
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {formatPercent(
                          backtestResult.risk_metrics.win_rate || 0,
                        )}
                      </div>
                    </div>

                    {/* Profit/Loss Ratio */}
                    <div className="bg-muted/50 rounded-lg p-4 md:col-span-2">
                      <div className="flex items-center text-muted-foreground mb-1">
                        <DollarSign className="h-4 w-4" />
                        <span className="text-sm ml-2">Profit/Loss Ratio</span>
                        <MetricTooltip content="平均盈利÷平均亏损。1.21表示赚钱时平均赚1.21元，亏钱时平均亏1元。配合胜率使用，即使胜率低于50%，高盈亏比也能盈利。" />
                      </div>
                      <div
                        className={`text-xl font-bold ${
                          (backtestResult.risk_metrics.profit_loss_ratio ||
                            0) >= 1
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {(
                          backtestResult.risk_metrics.profit_loss_ratio || 0
                        ).toFixed(2)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

          {/* Charts Section - Only show when we have chart data */}
          {backtestResult?.status === "success" && backtestResult.charts && (
            <>
              {/* Cumulative Returns Chart with Max Drawdown Annotation */}
              {backtestResult.charts.cumulative_returns &&
                backtestResult.charts.cumulative_returns.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg">
                        Cumulative Returns & Max Drawdown
                      </CardTitle>
                      <CardDescription>
                        Strategy performance over time
                        {backtestResult.charts.max_drawdown_info && (
                          <span className="ml-2">
                            <span className="text-red-600 font-medium">
                              Max Drawdown:{" "}
                              {formatPercent(
                                backtestResult.charts.max_drawdown_info
                                  .max_drawdown,
                              )}
                            </span>
                            <span className="text-muted-foreground ml-1">
                              (
                              {
                                backtestResult.charts.max_drawdown_info
                                  .peak_date
                              }{" "}
                              →{" "}
                              {
                                backtestResult.charts.max_drawdown_info
                                  .max_drawdown_date
                              }
                              {backtestResult.charts.max_drawdown_info
                                .drawdown_days > 0 &&
                                `, ${backtestResult.charts.max_drawdown_info.drawdown_days} days`}
                              {backtestResult.charts.max_drawdown_info
                                .recovery_date &&
                                `, recovered ${backtestResult.charts.max_drawdown_info.recovery_date}`}
                              )
                            </span>
                          </span>
                        )}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart
                            data={backtestResult.charts.cumulative_returns}
                          >
                            <defs>
                              <linearGradient
                                id="strategyGradient"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                              >
                                <stop
                                  offset="5%"
                                  stopColor="#22c55e"
                                  stopOpacity={0.3}
                                />
                                <stop
                                  offset="95%"
                                  stopColor="#22c55e"
                                  stopOpacity={0.05}
                                />
                              </linearGradient>
                            </defs>
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="date"
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value) => value.slice(5)}
                            />
                            <YAxis
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value: number) =>
                                `${(value * 100).toFixed(0)}%`
                              }
                            />
                            <RechartsTooltip
                              formatter={(value, name) => [
                                formatPercent(value as number),
                                name === "strategy" ? "Strategy" : "Benchmark",
                              ]}
                              labelFormatter={(label) => `Date: ${label}`}
                            />
                            <Legend />
                            <ReferenceLine
                              y={0}
                              stroke="#666"
                              strokeDasharray="3 3"
                            />
                            {/* Max Drawdown Peak Reference Line */}
                            {backtestResult.charts.max_drawdown_info && (
                              <ReferenceLine
                                x={
                                  backtestResult.charts.max_drawdown_info
                                    .peak_date
                                }
                                stroke="#f97316"
                                strokeDasharray="5 5"
                                strokeWidth={1.5}
                                label={{
                                  value: `Peak: ${formatPercent(backtestResult.charts.max_drawdown_info.peak_value)}`,
                                  position: "top",
                                  fill: "#f97316",
                                  fontSize: 10,
                                }}
                              />
                            )}
                            {/* Max Drawdown Trough Reference Line */}
                            {backtestResult.charts.max_drawdown_info && (
                              <ReferenceLine
                                x={
                                  backtestResult.charts.max_drawdown_info
                                    .max_drawdown_date
                                }
                                stroke="#dc2626"
                                strokeDasharray="5 5"
                                strokeWidth={1.5}
                              />
                            )}
                            <Area
                              type="monotone"
                              dataKey="strategy"
                              stroke="#22c55e"
                              strokeWidth={2}
                              fill="url(#strategyGradient)"
                              name="Strategy"
                            />
                            {backtestResult.charts.cumulative_returns[0]
                              ?.benchmark !== undefined && (
                              <Area
                                type="monotone"
                                dataKey="benchmark"
                                stroke="#3b82f6"
                                fill="#3b82f6"
                                fillOpacity={0.1}
                                name="Benchmark"
                              />
                            )}
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                      {/* Max Drawdown Summary Box */}
                      {backtestResult.charts.max_drawdown_info && (
                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-900">
                          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                            <TrendingDown className="h-4 w-4" />
                            <span className="font-medium">
                              Maximum Drawdown Analysis
                            </span>
                          </div>
                          <div className="mt-2 grid grid-cols-3 gap-3 text-sm">
                            <div>
                              <span className="text-muted-foreground">
                                Drawdown:
                              </span>
                              <span className="ml-1 font-medium text-red-600">
                                {formatPercent(
                                  backtestResult.charts.max_drawdown_info
                                    .max_drawdown,
                                )}
                              </span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">
                                Peak Date:
                              </span>
                              <span className="ml-1 font-medium">
                                {
                                  backtestResult.charts.max_drawdown_info
                                    .peak_date
                                }
                              </span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">
                                Trough Date:
                              </span>
                              <span className="ml-1 font-medium">
                                {
                                  backtestResult.charts.max_drawdown_info
                                    .max_drawdown_date
                                }
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

              {/* Return Distribution Chart */}
              {backtestResult.charts.return_distribution &&
                backtestResult.charts.return_distribution.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg">
                        Daily Return Distribution
                      </CardTitle>
                      <CardDescription>
                        Histogram of daily returns
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[250px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={backtestResult.charts.return_distribution}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="bin_center"
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value: number) =>
                                `${(value * 100).toFixed(1)}%`
                              }
                            />
                            <YAxis tick={{ fontSize: 11 }} />
                            <RechartsTooltip
                              formatter={(value) => [value, "Count"]}
                              labelFormatter={(label) =>
                                `Return: ${((label as number) * 100).toFixed(2)}%`
                              }
                            />
                            <Bar dataKey="count" fill="#8b5cf6" name="Count" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                )}

              {/* Enhanced Charts - Cumulative Returns */}
              {backtestResult?.status === "success" &&
                backtestResult.charts?.cumulative_returns && (
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-green-500" />
                        <CardTitle className="text-lg">
                          Cumulative Returns
                        </CardTitle>
                      </div>
                      <CardDescription>
                        Strategy performance over time
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={backtestResult.charts.cumulative_returns}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              dataKey="date"
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value) => {
                                const date = new Date(value);
                                return `${date.getMonth() + 1}/${date.getDate()}`;
                              }}
                            />
                            <YAxis
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value: number) =>
                                `${(value * 100).toFixed(1)}%`
                              }
                            />
                            <RechartsTooltip
                              formatter={(value: number) => [
                                `${(value * 100).toFixed(2)}%`,
                                "Cumulative Return",
                              ]}
                              labelFormatter={(label) => `Date: ${label}`}
                            />
                            <Line
                              type="monotone"
                              dataKey="cumulative_return"
                              stroke="#10b981"
                              strokeWidth={2}
                              dot={false}
                              name="Strategy"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                )}

              {/* Enhanced Charts - Daily Returns */}
              {backtestResult?.status === "success" &&
                backtestResult.charts?.daily_returns && (
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-2">
                        <Activity className="h-5 w-5 text-blue-500" />
                        <CardTitle className="text-lg">Daily Returns</CardTitle>
                      </div>
                      <CardDescription>
                        Daily return volatility and patterns
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={backtestResult.charts.daily_returns}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              dataKey="date"
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value) => {
                                const date = new Date(value);
                                return `${date.getMonth() + 1}/${date.getDate()}`;
                              }}
                            />
                            <YAxis
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value: number) =>
                                `${(value * 100).toFixed(1)}%`
                              }
                            />
                            <RechartsTooltip
                              formatter={(value: number) => [
                                `${(value * 100).toFixed(2)}%`,
                                "Daily Return",
                              ]}
                              labelFormatter={(label) => `Date: ${label}`}
                            />
                            <ReferenceLine
                              y={0}
                              stroke="#666"
                              strokeDasharray="2 2"
                            />
                            <Line
                              type="monotone"
                              dataKey="return"
                              stroke="#3b82f6"
                              strokeWidth={1}
                              dot={false}
                              name="Daily Return"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                )}

              {/* Enhanced Charts - Drawdown Analysis */}
              {backtestResult?.status === "success" &&
                backtestResult.charts?.max_drawdown_info && (
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-2">
                        <TrendingDown className="h-5 w-5 text-red-500" />
                        <CardTitle className="text-lg">
                          Drawdown Analysis
                        </CardTitle>
                      </div>
                      <CardDescription>
                        Maximum drawdown:{" "}
                        {(
                          backtestResult.charts.max_drawdown_info.max_drawdown *
                          100
                        ).toFixed(2)}
                        %
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
                          <div className="text-sm text-muted-foreground">
                            Peak Date
                          </div>
                          <div className="font-mono text-sm">
                            {backtestResult.charts.max_drawdown_info.peak_date}
                          </div>
                        </div>
                        <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
                          <div className="text-sm text-muted-foreground">
                            Trough Date
                          </div>
                          <div className="font-mono text-sm">
                            {
                              backtestResult.charts.max_drawdown_info
                                .max_drawdown_date
                            }
                          </div>
                        </div>
                        <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
                          <div className="text-sm text-muted-foreground">
                            Drawdown Days
                          </div>
                          <div className="font-mono text-sm">
                            {
                              backtestResult.charts.max_drawdown_info
                                .drawdown_days
                            }{" "}
                            days
                          </div>
                        </div>
                        <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
                          <div className="text-sm text-muted-foreground">
                            Recovery Date
                          </div>
                          <div className="font-mono text-sm">
                            {backtestResult.charts.max_drawdown_info
                              .recovery_date || "Not recovered"}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
