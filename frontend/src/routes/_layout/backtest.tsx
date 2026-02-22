import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Settings,
  Calendar,
  DollarSign,
  Percent,
  BarChart3,
} from "lucide-react";
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
import { OpenAPI } from "@/client";
import { toast } from "sonner";

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
          <div>
            <h1 className="text-2xl font-bold">Backtest</h1>
            <p className="text-muted-foreground">
              Evaluate strategy performance using historical data
            </p>
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
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="bg-muted/50 rounded-md p-2 text-sm">
                        <span className="text-muted-foreground">topk:</span>{" "}
                        <span className="font-medium">
                          {strategyConfig?.kwargs?.topk || "N/A"}
                        </span>
                      </div>
                      <div className="bg-muted/50 rounded-md p-2 text-sm">
                        <span className="text-muted-foreground">n_drop:</span>{" "}
                        <span className="font-medium">
                          {strategyConfig?.kwargs?.n_drop || "N/A"}
                        </span>
                      </div>
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
                              ? value.toLocaleString()
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

          {/* Run Backtest Button */}
          <div className="flex justify-center">
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
        </div>
      </div>
    </div>
  );
}
