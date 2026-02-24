import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Play,
  Loader2,
  Download,
  DollarSign,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OpenAPI } from "@/client";
import { toast } from "sonner";
import { useState, useEffect } from "react";

// API helper functions
const apiHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

async function fetchPortfolio() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/portfolio`,
    {
      headers: apiHeaders(),
    },
  );
  if (!response.ok) throw new Error("Failed to fetch portfolio");
  return response.json();
}

async function fetchTrades(limit: number = 100) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/trades?limit=${limit}`,
    { headers: apiHeaders() },
  );
  if (!response.ok) throw new Error("Failed to fetch trades");
  return response.json();
}

async function fetchPerformance() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/performance`,
    { headers: apiHeaders() },
  );
  if (!response.ok) throw new Error("Failed to fetch performance");
  return response.json();
}

async function executeTrades(dryRun: boolean = false) {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/paper-trading/execute`, {
    method: "POST",
    headers: apiHeaders(),
    body: JSON.stringify({ dry_run: dryRun }),
  });
  if (!response.ok) throw new Error("Failed to execute trades");
  return response.json();
}

async function resetPaperTrading() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/paper-trading/reset`, {
    method: "POST",
    headers: apiHeaders(),
  });
  if (!response.ok) throw new Error("Failed to reset paper trading");
  return response.json();
}

async function fetchOnlineStatus() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/online/status`, {
    headers: apiHeaders(),
  });
  if (!response.ok) throw new Error("Failed to fetch online status");
  return response.json();
}

async function fetchTradingPlan() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/paper-trading/plan`, {
    method: "POST",
    headers: apiHeaders(),
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new Error("Failed to fetch trading plan");
  return response.json();
}

interface SellOrder {
  instrument: string;
  direction: string;
  sell_pct: number;
  current_weight: number;
  reference_price: number;
  limit_price: number;
  score: number;
  reason: string;
  instruction: string;
}

interface BuyOrder {
  instrument: string;
  direction: string;
  target_weight: number;
  reference_price: number;
  limit_price: number;
  score: number;
  instruction: string;
  score_rank: number;
}

interface ExecutedTrade {
  instrument: string;
  direction: string;
  shares?: number;
  price?: number;
  value?: number;
  sell_pct?: number;
  target_weight?: number;
  executed_at?: string;
}

interface LastExecutedTrades {
  sells: ExecutedTrade[];
  buys: ExecutedTrade[];
  sell_count: number;
  buy_count: number;
}

interface TradingPlanData {
  success: boolean;
  date?: string;
  generated_at?: string;
  strategy: string;
  topk: number;
  n_drop: number;
  target_weight_per_stock: number;
  slippage: number;
  portfolio_summary?: {
    total_value: number;
    cash: number;
    position_value: number;
    position_count: number;
  };
  sell_orders: SellOrder[];
  buy_orders: BuyOrder[];
  summary?: {
    sell_count: number;
    buy_count: number;
  };
  last_executed_trades?: LastExecutedTrades;
  error?: string;
}

interface OnlineStatus {
  config: {
    region?: string;
    [key: string]: unknown;
  };
}

// Types
interface Position {
  instrument: string;
  shares: number;
  avg_cost: number;
  current_value: number;
}

interface PortfolioData {
  success: boolean;
  cash: number;
  positions: Position[];
  position_count: number;
  total_position_value: number;
  total_value: number;
  created_at?: string;
  updated_at?: string;
  error?: string;
}

interface TradeItem {
  date: string;
  instrument: string;
  action: string;
  shares: number;
  price: number;
  value: number;
  sell_pct?: number;
  target_weight?: number;
  executed_at: string;
}

interface TradesData {
  success: boolean;
  total_trades: number;
  trades: TradeItem[];
  error?: string;
}

interface PerformanceData {
  success: boolean;
  initial_cash: number;
  current_value: number;
  total_return: number;
  total_return_pct: string;
  total_trades: number;
  buy_trades: number;
  sell_trades: number;
  trading_days: number;
  position_count: number;
  // Extended metrics
  annualized_return?: number;
  annualized_return_pct?: string;
  max_drawdown?: number;
  max_drawdown_pct?: string;
  sharpe_ratio?: number;
  win_rate?: number;
  win_rate_pct?: string;
  error?: string;
}

interface TradingPlanSummary {
  sell_orders: SellOrder[];
  buy_orders: BuyOrder[];
  hold_orders: Array<{
    instrument: string;
    direction: string;
    current_weight: number;
    target_weight: number;
    score: number;
    score_rank: number;
  }>;
  summary: {
    sell_count: number;
    buy_count: number;
    hold_count: number;
  };
}

interface ExecuteResult {
  success: boolean;
  date?: string;
  dry_run: boolean;
  slippage: number;
  sells_executed: number;
  buys_executed: number;
  executed_sells: TradeItem[];
  executed_buys: TradeItem[];
  final_cash: number;
  final_position_count: number;
  trading_plan?: TradingPlanSummary;
  error?: string;
}

const LAST_EXECUTE_KEY = "quantbot_last_execute_result";

function PaperTradingPage() {
  const queryClient = useQueryClient();
  const [lastExecuteResult, setLastExecuteResult] =
    useState<ExecuteResult | null>(() => {
      try {
        const saved = localStorage.getItem(LAST_EXECUTE_KEY);
        return saved ? JSON.parse(saved) : null;
      } catch {
        return null;
      }
    });

  useEffect(() => {
    if (lastExecuteResult) {
      localStorage.setItem(LAST_EXECUTE_KEY, JSON.stringify(lastExecuteResult));
    }
  }, [lastExecuteResult]);

  // Queries
  const { data: portfolio, isLoading: portfolioLoading } =
    useQuery<PortfolioData>({
      queryKey: ["paperTradingPortfolio"],
      queryFn: fetchPortfolio,
      staleTime: 30000,
      refetchOnWindowFocus: false,
    });

  const { data: trades, isLoading: tradesLoading } = useQuery<TradesData>({
    queryKey: ["paperTradingTrades"],
    queryFn: () => fetchTrades(50),
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });

  const { data: performance, isLoading: performanceLoading } =
    useQuery<PerformanceData>({
      queryKey: ["paperTradingPerformance"],
      queryFn: fetchPerformance,
      staleTime: 30000,
      refetchOnWindowFocus: false,
    });

  // Mutations
  const executeMutation = useMutation<ExecuteResult>({
    mutationFn: () => executeTrades(false),
    onSuccess: async (data) => {
      setLastExecuteResult(data);
      if (data.success) {
        toast.success("Trades executed successfully", {
          description: `Sells: ${data.sells_executed}, Buys: ${data.buys_executed}`,
        });
        // Force refetch all queries immediately
        await queryClient.refetchQueries({
          queryKey: ["paperTradingPortfolio"],
        });
        await queryClient.refetchQueries({ queryKey: ["paperTradingTrades"] });
        await queryClient.refetchQueries({
          queryKey: ["paperTradingPerformance"],
        });
        await queryClient.refetchQueries({ queryKey: ["paperTradingPlan"] });
      } else {
        toast.error("Trade execution failed", { description: data.error });
      }
    },
    onError: (error) => {
      toast.error("Failed to execute trades", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    },
  });

  const resetMutation = useMutation({
    mutationFn: resetPaperTrading,
    onSuccess: async (data) => {
      if (data.success) {
        toast.success("Paper trading reset", { description: data.message });
        setLastExecuteResult(null);
        localStorage.removeItem(LAST_EXECUTE_KEY);
        // Force refetch all queries immediately
        await queryClient.refetchQueries({
          queryKey: ["paperTradingPortfolio"],
        });
        await queryClient.refetchQueries({ queryKey: ["paperTradingTrades"] });
        await queryClient.refetchQueries({
          queryKey: ["paperTradingPerformance"],
        });
        await queryClient.refetchQueries({ queryKey: ["paperTradingPlan"] });
      } else {
        toast.error("Reset failed", { description: data.error });
      }
    },
    onError: (error) => {
      toast.error("Failed to reset", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    },
  });

  // Fetch online status for region
  const { data: onlineStatus } = useQuery<OnlineStatus>({
    queryKey: ["onlineStatus"],
    queryFn: fetchOnlineStatus,
  });

  // Fetch trading plan
  const { data: tradingPlan, isLoading: planLoading } =
    useQuery<TradingPlanData>({
      queryKey: ["paperTradingPlan"],
      queryFn: fetchTradingPlan,
      staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      refetchOnWindowFocus: false,
    });

  const region = onlineStatus?.config?.region || "us";

  const formatCurrency = (value: number) => {
    const currencyConfig =
      region === "cn"
        ? { locale: "zh-CN", currency: "CNY" }
        : { locale: "en-US", currency: "USD" };

    return new Intl.NumberFormat(currencyConfig.locale, {
      style: "currency",
      currency: currencyConfig.currency,
      minimumFractionDigits: 2,
    }).format(value);
  };

  const exportTradesToCSV = () => {
    if (!trades?.trades?.length) {
      toast.error("No trades to export");
      return;
    }

    const headers = [
      "Date",
      "Instrument",
      "Action",
      "Shares",
      "Price",
      "Value",
      "Executed At",
    ];
    const rows = trades.trades.map((t) => [
      t.date,
      t.instrument,
      t.action,
      t.shares,
      t.price.toFixed(4),
      t.value.toFixed(2),
      t.executed_at,
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((r) => r.join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `paper_trades_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    toast.success("Trades exported to CSV");
  };

  const getActionIcon = (action: string) => {
    switch (action.toUpperCase()) {
      case "BUY":
        return <ArrowUpRight className="h-4 w-4 text-green-500" />;
      case "SELL":
        return <ArrowDownRight className="h-4 w-4 text-red-500" />;
      default:
        return <Minus className="h-4 w-4 text-gray-500" />;
    }
  };

  const getActionBadge = (action: string) => {
    switch (action.toUpperCase()) {
      case "BUY":
        return <Badge className="bg-green-500">BUY</Badge>;
      case "SELL":
        return <Badge className="bg-red-500">SELL</Badge>;
      default:
        return <Badge variant="secondary">{action}</Badge>;
    }
  };

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                Paper Trading
              </h1>
              <p className="text-muted-foreground">
                Simulated trading with real-time signals
              </p>
            </div>
            <Button
              onClick={() => executeMutation.mutate()}
              disabled={executeMutation.isPending}
            >
              {executeMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Execute Trades
            </Button>
          </div>

          {/* Performance Overview */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Value
                </CardTitle>
                <Wallet className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {portfolioLoading
                    ? "-"
                    : formatCurrency(portfolio?.total_value || 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  Cash: {formatCurrency(portfolio?.cash || 0)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Return
                </CardTitle>
                {(performance?.total_return || 0) >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-500" />
                )}
              </CardHeader>
              <CardContent>
                <div
                  className={`text-2xl font-bold ${
                    (performance?.total_return || 0) >= 0
                      ? "text-green-600"
                      : "text-red-600"
                  }`}
                >
                  {performanceLoading
                    ? "-"
                    : performance?.total_return_pct || "0.00%"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatCurrency(performance?.total_return || 0)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Positions</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {portfolioLoading ? "-" : portfolio?.position_count || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Value: {formatCurrency(portfolio?.total_position_value || 0)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Trades
                </CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {performanceLoading ? "-" : performance?.total_trades || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Buy: {performance?.buy_trades || 0} | Sell:{" "}
                  {performance?.sell_trades || 0}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Trading Days Warning */}
          {performance &&
            performance.trading_days < 30 &&
            performance.trading_days > 0 && (
              <Card className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
                <CardContent className="flex items-center gap-2 py-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-600" />
                  <span className="text-yellow-700 dark:text-yellow-300">
                    Only {performance.trading_days} trading days. Performance
                    metrics are for reference only (recommend &gt; 30 days).
                  </span>
                </CardContent>
              </Card>
            )}

          {/* Performance Metrics */}
          <Card>
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
              <CardDescription>
                Trading performance since inception
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Initial Cash</p>
                  <p className="text-lg font-semibold">
                    {formatCurrency(performance?.initial_cash || 0)}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Current Value</p>
                  <p className="text-lg font-semibold">
                    {formatCurrency(performance?.current_value || 0)}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    Cumulative Return
                  </p>
                  <p
                    className={`text-lg font-semibold ${(performance?.total_return || 0) >= 0 ? "text-green-600" : "text-red-600"}`}
                  >
                    {performance?.total_return_pct || "0.00%"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    Annualized Return
                  </p>
                  <p
                    className={`text-lg font-semibold ${(performance?.annualized_return || 0) >= 0 ? "text-green-600" : "text-red-600"}`}
                  >
                    {performance?.annualized_return_pct || "-"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Max Drawdown</p>
                  <p className="text-lg font-semibold text-red-600">
                    {performance?.max_drawdown_pct || "-"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
                  <p className="text-lg font-semibold">
                    {performance?.sharpe_ratio?.toFixed(2) || "-"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Trading Days</p>
                  <p className="text-lg font-semibold">
                    {performance?.trading_days || 0}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    Position Count
                  </p>
                  <p className="text-lg font-semibold">
                    {performance?.position_count || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Main Content Tabs */}
          <Tabs defaultValue="plan" className="space-y-4">
            <TabsList>
              <TabsTrigger value="plan">Trading Plan</TabsTrigger>
              <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
              <TabsTrigger value="trades">Trade History</TabsTrigger>
            </TabsList>

            {/* Trading Plan Tab */}
            <TabsContent value="plan" className="space-y-4">
              {planLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : tradingPlan?.success ? (
                <>
                  {/* Plan Summary */}
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle>Trading Plan</CardTitle>
                          <CardDescription>
                            {tradingPlan.strategy} | Date: {tradingPlan.date} |
                            Generated: {tradingPlan.generated_at}
                          </CardDescription>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          <Badge variant="secondary">
                            TopK: {tradingPlan.topk}
                          </Badge>
                          <Badge variant="secondary">
                            N_Drop: {tradingPlan.n_drop}
                          </Badge>
                          <Badge variant="secondary">
                            Weight:{" "}
                            {tradingPlan.target_weight_per_stock?.toFixed(2)}%
                          </Badge>
                          <Badge variant="secondary">
                            Slippage:{" "}
                            {((tradingPlan.slippage || 0) * 100).toFixed(2)}%
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Portfolio Summary */}
                      {tradingPlan.portfolio_summary && (
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">
                              Total Value:{" "}
                            </span>
                            <span className="font-medium">
                              {formatCurrency(
                                tradingPlan.portfolio_summary.total_value,
                              )}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Cash:{" "}
                            </span>
                            <span className="font-medium">
                              {formatCurrency(
                                tradingPlan.portfolio_summary.cash,
                              )}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Position Value:{" "}
                            </span>
                            <span className="font-medium">
                              {formatCurrency(
                                tradingPlan.portfolio_summary.position_value,
                              )}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">
                              Positions:{" "}
                            </span>
                            <span className="font-medium">
                              {tradingPlan.portfolio_summary.position_count}
                            </span>
                          </div>
                        </div>
                      )}
                      {/* Order Summary - Show last executed trades if available, otherwise show pending orders */}
                      {tradingPlan.last_executed_trades &&
                      (tradingPlan.last_executed_trades.sell_count > 0 ||
                        tradingPlan.last_executed_trades.buy_count > 0) ? (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-red-50 dark:bg-red-950 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-red-600">
                              {tradingPlan.last_executed_trades.sell_count}
                            </div>
                            <div className="text-sm text-red-600">
                              Executed Sells
                            </div>
                          </div>
                          <div className="bg-green-50 dark:bg-green-950 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-green-600">
                              {tradingPlan.last_executed_trades.buy_count}
                            </div>
                            <div className="text-sm text-green-600">
                              Executed Buys
                            </div>
                          </div>
                        </div>
                      ) : tradingPlan.summary ? (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-red-50 dark:bg-red-950 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-red-600">
                              {tradingPlan.summary.sell_count}
                            </div>
                            <div className="text-sm text-red-600">
                              Sell Orders
                            </div>
                          </div>
                          <div className="bg-green-50 dark:bg-green-950 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-green-600">
                              {tradingPlan.summary.buy_count}
                            </div>
                            <div className="text-sm text-green-600">
                              Buy Orders
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>

                  {/* Sell Orders */}
                  {tradingPlan.sell_orders?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-red-600">
                          Sell Orders ({tradingPlan.sell_orders.length})
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Instrument</TableHead>
                              <TableHead>Direction</TableHead>
                              <TableHead className="text-right">
                                Sell %
                              </TableHead>
                              <TableHead className="text-right">
                                Current Weight
                              </TableHead>
                              <TableHead className="text-right">
                                Limit Price
                              </TableHead>
                              <TableHead>Instruction</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {tradingPlan.sell_orders.map((order) => (
                              <TableRow key={order.instrument}>
                                <TableCell className="font-medium">
                                  {order.instrument}
                                </TableCell>
                                <TableCell className="text-red-600">
                                  {order.direction}
                                </TableCell>
                                <TableCell className="text-right">
                                  {order.sell_pct.toFixed(0)}%
                                </TableCell>
                                <TableCell className="text-right">
                                  {order.current_weight.toFixed(2)}%
                                </TableCell>
                                <TableCell className="text-right">
                                  {order.limit_price.toFixed(2)}
                                </TableCell>
                                <TableCell className="max-w-md text-sm">
                                  {order.instruction}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  )}

                  {/* Buy Orders */}
                  {tradingPlan.buy_orders?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-green-600">
                          Buy Orders ({tradingPlan.buy_orders.length})
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Instrument</TableHead>
                              <TableHead>Direction</TableHead>
                              <TableHead className="text-right">
                                Target Weight
                              </TableHead>
                              <TableHead className="text-right">
                                Limit Price
                              </TableHead>
                              <TableHead>Instruction</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {tradingPlan.buy_orders.map((order) => (
                              <TableRow key={order.instrument}>
                                <TableCell className="font-medium">
                                  {order.instrument}
                                </TableCell>
                                <TableCell className="text-green-600">
                                  {order.direction}
                                </TableCell>
                                <TableCell className="text-right">
                                  {order.target_weight.toFixed(2)}%
                                </TableCell>
                                <TableCell className="text-right">
                                  {order.limit_price.toFixed(2)}
                                </TableCell>
                                <TableCell className="max-w-md text-sm">
                                  {order.instruction}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  )}

                  {/* Last Executed Buys - Show when no pending buy orders but have executed buys */}
                  {(tradingPlan.last_executed_trades?.buys?.length ?? 0) > 0 &&
                    (tradingPlan.buy_orders?.length ?? 0) === 0 && (
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-green-600">
                            Last Executed Buys (
                            {tradingPlan.last_executed_trades?.buys?.length ??
                              0}
                            )
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Instrument</TableHead>
                                <TableHead>Direction</TableHead>
                                <TableHead className="text-right">
                                  Shares
                                </TableHead>
                                <TableHead className="text-right">
                                  Price
                                </TableHead>
                                <TableHead className="text-right">
                                  Value
                                </TableHead>
                                <TableHead className="text-right">
                                  Target Weight
                                </TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(
                                tradingPlan.last_executed_trades?.buys ?? []
                              ).map((trade) => (
                                <TableRow key={trade.instrument}>
                                  <TableCell className="font-medium">
                                    {trade.instrument}
                                  </TableCell>
                                  <TableCell className="text-green-600">
                                    {trade.direction}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.shares?.toLocaleString()}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.price?.toFixed(2)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {formatCurrency(trade.value || 0)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.target_weight?.toFixed(2)}%
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </Card>
                    )}

                  {/* Last Executed Sells - Show when no pending sell orders but have executed sells */}
                  {(tradingPlan.last_executed_trades?.sells?.length ?? 0) > 0 &&
                    (tradingPlan.sell_orders?.length ?? 0) === 0 && (
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-red-600">
                            Last Executed Sells (
                            {tradingPlan.last_executed_trades?.sells?.length ??
                              0}
                            )
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Instrument</TableHead>
                                <TableHead>Direction</TableHead>
                                <TableHead className="text-right">
                                  Shares
                                </TableHead>
                                <TableHead className="text-right">
                                  Price
                                </TableHead>
                                <TableHead className="text-right">
                                  Value
                                </TableHead>
                                <TableHead className="text-right">
                                  Sell %
                                </TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(
                                tradingPlan.last_executed_trades?.sells ?? []
                              ).map((trade) => (
                                <TableRow key={trade.instrument}>
                                  <TableCell className="font-medium">
                                    {trade.instrument}
                                  </TableCell>
                                  <TableCell className="text-red-600">
                                    {trade.direction}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.shares?.toLocaleString()}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.price?.toFixed(2)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {formatCurrency(trade.value || 0)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.sell_pct?.toFixed(0)}%
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </Card>
                    )}
                </>
              ) : tradingPlan?.last_executed_trades &&
                (tradingPlan.last_executed_trades.buy_count > 0 ||
                  tradingPlan.last_executed_trades.sell_count > 0) ? (
                <>
                  {/* Order Summary */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Last Executed Trades</CardTitle>
                      <CardDescription>
                        Most recent executed trades from the last trading
                        session
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-red-50 dark:bg-red-950 rounded-lg p-3 text-center">
                          <div className="text-2xl font-bold text-red-600">
                            {tradingPlan.last_executed_trades.sell_count}
                          </div>
                          <div className="text-sm text-red-600">
                            Executed Sells
                          </div>
                        </div>
                        <div className="bg-green-50 dark:bg-green-950 rounded-lg p-3 text-center">
                          <div className="text-2xl font-bold text-green-600">
                            {tradingPlan.last_executed_trades.buy_count}
                          </div>
                          <div className="text-sm text-green-600">
                            Executed Buys
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Last Executed Buys */}
                  {(tradingPlan.last_executed_trades?.buys?.length ?? 0) >
                    0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-green-600">
                          Last Executed Buys (
                          {tradingPlan.last_executed_trades?.buys?.length ?? 0})
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Instrument</TableHead>
                              <TableHead>Direction</TableHead>
                              <TableHead className="text-right">
                                Shares
                              </TableHead>
                              <TableHead className="text-right">
                                Price
                              </TableHead>
                              <TableHead className="text-right">
                                Value
                              </TableHead>
                              <TableHead className="text-right">
                                Target Weight
                              </TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(tradingPlan.last_executed_trades?.buys ?? []).map(
                              (trade) => (
                                <TableRow key={trade.instrument}>
                                  <TableCell className="font-medium">
                                    {trade.instrument}
                                  </TableCell>
                                  <TableCell className="text-green-600">
                                    {trade.direction}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.shares?.toLocaleString()}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.price?.toFixed(2)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {formatCurrency(trade.value || 0)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {trade.target_weight?.toFixed(2)}%
                                  </TableCell>
                                </TableRow>
                              ),
                            )}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  )}

                  {/* Last Executed Sells */}
                  {(tradingPlan.last_executed_trades?.sells?.length ?? 0) >
                    0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-red-600">
                          Last Executed Sells (
                          {tradingPlan.last_executed_trades?.sells?.length ?? 0}
                          )
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Instrument</TableHead>
                              <TableHead>Direction</TableHead>
                              <TableHead className="text-right">
                                Shares
                              </TableHead>
                              <TableHead className="text-right">
                                Price
                              </TableHead>
                              <TableHead className="text-right">
                                Value
                              </TableHead>
                              <TableHead className="text-right">
                                Sell %
                              </TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(
                              tradingPlan.last_executed_trades?.sells ?? []
                            ).map((trade) => (
                              <TableRow key={trade.instrument}>
                                <TableCell className="font-medium">
                                  {trade.instrument}
                                </TableCell>
                                <TableCell className="text-red-600">
                                  {trade.direction}
                                </TableCell>
                                <TableCell className="text-right">
                                  {trade.shares?.toLocaleString()}
                                </TableCell>
                                <TableCell className="text-right">
                                  {trade.price?.toFixed(2)}
                                </TableCell>
                                <TableCell className="text-right">
                                  {formatCurrency(trade.value || 0)}
                                </TableCell>
                                <TableCell className="text-right">
                                  {trade.sell_pct?.toFixed(0)}%
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                <Card>
                  <CardContent className="py-8 text-center">
                    <p className="text-muted-foreground">
                      No trading data available. Click "Execute Trades" to
                      start.
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Portfolio Tab */}
            <TabsContent value="portfolio" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Current Holdings</CardTitle>
                  <CardDescription>
                    {portfolio?.position_count || 0} positions | Updated:{" "}
                    {portfolio?.updated_at || "-"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {portfolioLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin" />
                    </div>
                  ) : portfolio?.positions?.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Instrument</TableHead>
                          <TableHead className="text-right">Shares</TableHead>
                          <TableHead className="text-right">Avg Cost</TableHead>
                          <TableHead className="text-right">
                            Current Value
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {portfolio.positions.map((pos) => (
                          <TableRow key={pos.instrument}>
                            <TableCell className="font-medium">
                              {pos.instrument}
                            </TableCell>
                            <TableCell className="text-right">
                              {pos.shares.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right">
                              {pos.avg_cost.toFixed(4)}
                            </TableCell>
                            <TableCell className="text-right">
                              {formatCurrency(pos.current_value)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">
                      No positions. Execute trades to start paper trading.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Trades Tab */}
            <TabsContent value="trades" className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Trade History</CardTitle>
                      <CardDescription>
                        {trades?.total_trades || 0} total trades
                      </CardDescription>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={exportTradesToCSV}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Export CSV
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {tradesLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin" />
                    </div>
                  ) : trades?.trades?.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date</TableHead>
                          <TableHead>Instrument</TableHead>
                          <TableHead>Action</TableHead>
                          <TableHead className="text-right">Shares</TableHead>
                          <TableHead className="text-right">Price</TableHead>
                          <TableHead className="text-right">Value</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {trades.trades.slice(0, 50).map((trade, idx) => (
                          <TableRow
                            key={`${trade.instrument}-${trade.executed_at}-${idx}`}
                          >
                            <TableCell>{trade.date}</TableCell>
                            <TableCell className="font-medium">
                              {trade.instrument}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                {getActionIcon(trade.action)}
                                {getActionBadge(trade.action)}
                              </div>
                            </TableCell>
                            <TableCell className="text-right">
                              {trade.shares.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right">
                              {trade.price.toFixed(4)}
                            </TableCell>
                            <TableCell className="text-right">
                              {formatCurrency(trade.value)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">
                      No trades yet. Execute trades to see history.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Last Execute Result */}
          {lastExecuteResult && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {lastExecuteResult.success ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <CardTitle>Last Execution Result</CardTitle>
                  </div>
                  <Badge
                    variant={
                      lastExecuteResult.dry_run ? "secondary" : "default"
                    }
                  >
                    {lastExecuteResult.dry_run ? "Dry Run" : "Executed"}
                  </Badge>
                </div>
                <CardDescription>
                  Date: {lastExecuteResult.date} | Sells:{" "}
                  {lastExecuteResult.sells_executed} | Buys:{" "}
                  {lastExecuteResult.buys_executed}
                </CardDescription>
              </CardHeader>
              {lastExecuteResult.error && (
                <CardContent>
                  <div className="p-4 bg-destructive/10 text-destructive rounded-md">
                    {lastExecuteResult.error}
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Reset Button */}
          <div className="flex justify-end">
            <Button
              variant="destructive"
              size="sm"
              disabled={resetMutation.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    "Reset Paper Trading?\n\nThis will clear all positions, trades, and daily records. This action cannot be undone.",
                  )
                ) {
                  resetMutation.mutate();
                }
              }}
            >
              {resetMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Reset Paper Trading
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/_layout/paper-trading")({
  component: PaperTradingPage,
});
