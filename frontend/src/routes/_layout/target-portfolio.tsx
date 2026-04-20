import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  Loader2,
  TrendingUp,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { OpenAPI } from "@/client";
import { useMemo } from "react";

// Types for TopK Strategy
interface TopKPosition {
  rank: number;
  symbol: string;
  name: string;
  type: "stock";
  weight: number;
  score: number;
  target_value: number;
  target_shares: number;
  action: "buy" | "sell" | "hold";
  reason?: string;
  original_weight?: number;
}

interface TopKSummary {
  total_positions: number;
  buy_count: number;
  sell_count: number;
  hold_count: number;
}

interface TopKPortfolioData {
  trade_date: string;
  signal_for_date: string;
  generated_at: string;
  total_value: number;
  rebalance_summary: TopKSummary;
  buy_positions: TopKPosition[];
  sell_positions: TopKPosition[];
  hold_positions: TopKPosition[];
  final_positions: TopKPosition[];
  summary: TopKSummary;
}

interface RoutineResult {
  success: boolean;
  cur_time?: string;
  executed_at?: string;
  total_duration_seconds?: number;
  signal_count?: number;
  error?: string;
  // ETF Enhanced Indexing format - matches JSON output
  generated_at?: string;
  trade_date?: string;
  signal_for_date?: string;
  total_value?: number;
  region?: string;
  lot_size?: number;
  weights?: PortfolioWeights;
  target_portfolio?: PortfolioPosition[];
  portfolio_summary?: PortfolioSummary;
  strategy?: string;
}

// API helper functions
const apiHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

async function fetchNotificationConfig() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/config`,
    { headers: apiHeaders() },
  );
  if (!response.ok) throw new Error("Failed to fetch notification config");
  return response.json();
}

async function updateNotificationConfig(config: {
  enabled?: boolean;
  recipients?: string[];
}) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/config`,
    {
      method: "PUT",
      headers: apiHeaders(),
      body: JSON.stringify(config),
    },
  );
  if (!response.ok) throw new Error("Failed to update notification config");
  return response.json();
}

async function addRecipient(email: string) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/recipient`,
    {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({ email }),
    },
  );
  if (!response.ok) throw new Error("Failed to add recipient");
  return response.json();
}

async function removeRecipient(email: string) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/recipient/${encodeURIComponent(email)}`,
    {
      method: "DELETE",
      headers: apiHeaders(),
    },
  );
  if (!response.ok) throw new Error("Failed to remove recipient");
  return response.json();
}

async function sendTestEmail(recipient?: string) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/test`,
    {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({ recipient }),
    },
  );
  if (!response.ok) throw new Error("Failed to send test email");
  return response.json();
}

async function fetchLatestPortfolio() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/dashboard/latest-portfolio`,
    { headers: apiHeaders() },
  );
  if (!response.ok) throw new Error("Failed to fetch latest portfolio");
  return response.json();
}

// TopK Strategy Portfolio Section Component - Shows buy/sell/hold/final positions separately
function TopKPortfolioSection({
  portfolioData,
}: {
  portfolioData: TopKPortfolioData | null;
}) {
  if (!portfolioData) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-muted-foreground">
            <div className="text-4xl mb-2">📊</div>
            <p className="font-medium">No Portfolio Data</p>
            <p className="text-sm">Run Daily Task to generate TopK portfolio</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { buy_positions, sell_positions, hold_positions, final_positions, summary } = portfolioData;

  // Render position table for each section
  const renderPositionTable = (
    positions: TopKPosition[],
    sectionType: "buy" | "sell" | "hold" | "final"
  ) => {
    if (positions.length === 0 && sectionType !== "final") {
      return (
        <div className="text-center py-4 text-muted-foreground">
          <p className="text-sm">No {sectionType} positions</p>
        </div>
      );
    }

    const config = {
      buy: {
        title: "买入股票",
        emoji: "🟢",
        headerBg: "bg-green-600",
        borderColor: "border-green-200 dark:border-green-800",
        columns: ["代码", "名称", "预测分数", "目标权重", "目标金额"],
      },
      sell: {
        title: "卖出股票", 
        emoji: "🔴",
        headerBg: "bg-red-600",
        borderColor: "border-red-200 dark:border-red-800",
        columns: ["代码", "名称", "卖出原因", "原权重"],
      },
      hold: {
        title: "持有股票",
        emoji: "🟡", 
        headerBg: "bg-yellow-600",
        borderColor: "border-yellow-200 dark:border-yellow-800",
        columns: ["排名", "代码", "名称", "预测分数", "权重"],
      },
      final: {
        title: "最新持仓总览",
        emoji: "📊",
        headerBg: "bg-blue-600", 
        borderColor: "border-blue-200 dark:border-blue-800",
        columns: ["排名", "代码", "名称", "预测分数", "权重", "目标金额"],
      },
    };

    const c = config[sectionType];

    return (
      <div className="mb-6">
        <div className={`${c.headerBg} text-white px-4 py-3 rounded-t-lg font-semibold flex items-center gap-2`}>
          <span>{c.emoji}</span>
          <span>{c.title} ({positions.length}只)</span>
        </div>
        <div className={`border ${c.borderColor} border-t-0 rounded-b-lg overflow-hidden`}>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                {c.columns.map((col, idx) => (
                  <th key={idx} className="h-10 px-3 text-left font-medium">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, index) => (
                <tr
                  key={pos.symbol || index}
                  className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900/30"
                >
                  {sectionType === "buy" && (
                    <>
                      <td className="px-3 py-3 font-mono font-bold">{pos.symbol}</td>
                      <td className="px-3 py-3">{pos.name}</td>
                      <td className="px-3 py-3 text-right font-medium">{pos.score?.toFixed(4)}</td>
                      <td className="px-3 py-3 text-right font-medium">{pos.weight?.toFixed(2)}%</td>
                      <td className="px-3 py-3 text-right">¥{pos.target_value?.toLocaleString()}</td>
                    </>
                  )}
                  {sectionType === "sell" && (
                    <>
                      <td className="px-3 py-3 font-mono font-bold">{pos.symbol}</td>
                      <td className="px-3 py-3">{pos.name}</td>
                      <td className="px-3 py-3">{pos.reason || "排名下降"}</td>
                      <td className="px-3 py-3 text-right">{pos.original_weight?.toFixed(2)}%</td>
                    </>
                  )}
                  {sectionType === "hold" && (
                    <>
                      <td className="px-3 py-3 text-center font-bold">{pos.rank}</td>
                      <td className="px-3 py-3 font-mono font-bold">{pos.symbol}</td>
                      <td className="px-3 py-3">{pos.name}</td>
                      <td className="px-3 py-3 text-right font-medium">{pos.score?.toFixed(4)}</td>
                      <td className="px-3 py-3 text-right font-medium">{pos.weight?.toFixed(2)}%</td>
                    </>
                  )}
                  {sectionType === "final" && (
                    <>
                      <td className="px-3 py-3 text-center font-bold">{pos.rank}</td>
                      <td className="px-3 py-3 font-mono font-bold">{pos.symbol}</td>
                      <td className="px-3 py-3">{pos.name}</td>
                      <td className="px-3 py-3 text-right font-medium">{pos.score?.toFixed(4)}</td>
                      <td className="px-3 py-3 text-right font-medium">{pos.weight?.toFixed(2)}%</td>
                      <td className="px-3 py-3 text-right">¥{pos.target_value?.toLocaleString()}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Portfolio Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-600" />
            TopK策略组合 - {portfolioData.signal_for_date}
          </CardTitle>
          <CardDescription>
            生成时间: {portfolioData.generated_at} | 总资金: ¥{portfolioData.total_value?.toLocaleString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
              <div className="text-sm text-muted-foreground">买入</div>
              <div className="text-2xl font-bold text-green-600">{summary.buy_count}</div>
            </div>
            <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
              <div className="text-sm text-muted-foreground">卖出</div>
              <div className="text-2xl font-bold text-red-600">{summary.sell_count}</div>
            </div>
            <div className="bg-yellow-50 dark:bg-yellow-950/30 rounded-lg p-3">
              <div className="text-sm text-muted-foreground">持有</div>
              <div className="text-2xl font-bold text-yellow-600">{summary.hold_count}</div>
            </div>
            <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-3">
              <div className="text-sm text-muted-foreground">总持仓</div>
              <div className="text-2xl font-bold text-blue-600">{summary.total_positions}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Buy Positions */}
      {renderPositionTable(buy_positions, "buy")}

      {/* Sell Positions */}
      {renderPositionTable(sell_positions, "sell")}

      {/* Hold Positions (show top 10) */}
      {renderPositionTable(hold_positions.slice(0, 10), "hold")}
      {hold_positions.length > 10 && (
        <div className="text-center text-sm text-muted-foreground mb-4">
          * 显示前10只持有股票，共{hold_positions.length}只
        </div>
      )}

      {/* Final Positions Overview */}
      {renderPositionTable(final_positions, "final")}
    </div>
  );
}

export const Route = createFileRoute("/_layout/target-portfolio")({
  component: TargetPortfolioPage,
  head: () => ({
    meta: [{ title: "Target Portfolio - QuantBot" }],
  }),
});

function TargetPortfolioPage() {
  const queryClient = useQueryClient();
  const [newEmail, setNewEmail] = useState("");

  // Fetch latest portfolio from API
  const {
    data: latestPortfolio,
    isLoading: portfolioLoading,
    error: portfolioError,
  } = useQuery({
    queryKey: ["latestPortfolio"],
    queryFn: fetchLatestPortfolio,
    refetchOnWindowFocus: true,
    staleTime: 30000, // 30 seconds
  });

  // Transform API data to TopK format
  const topkPortfolioData: TopKPortfolioData | null = useMemo(() => {
    if (!latestPortfolio?.success) return null;
    
    // For now, create mock data structure until backend provides TopK format
    // TODO: Update when backend provides proper TopK portfolio data
    return {
      trade_date: latestPortfolio.trade_date || "",
      signal_for_date: latestPortfolio.signal_for_date || "",
      generated_at: latestPortfolio.generated_at || "",
      total_value: latestPortfolio.total_value || 1000000,
      rebalance_summary: {
        total_positions: 30,
        buy_count: 5,
        sell_count: 5,
        hold_count: 20,
      },
      buy_positions: [], // TODO: Get from backend
      sell_positions: [], // TODO: Get from backend  
      hold_positions: [], // TODO: Get from backend
      final_positions: latestPortfolio.positions || [],
      summary: {
        total_positions: 30,
        buy_count: 5,
        sell_count: 5,
        hold_count: 20,
      },
    };
  }, [latestPortfolio]);

  // Query for notification config
  const {
    data: configData,
    isLoading: configLoading,
    error: configError,
  } = useQuery({
    queryKey: ["notificationConfig"],
    queryFn: fetchNotificationConfig,
  ) => {
    if (items.length === 0) return null;

    const config = {
      buy: {
        title: "Buy Orders",
        emoji: "🟢",
        headerBg: "bg-green-500",
        borderColor: "border-green-200 dark:border-green-800",
        rowHover: "hover:bg-green-50 dark:hover:bg-green-950/30",
      },
      sell: {
        title: "Sell Orders",
        emoji: "🔴",
        headerBg: "bg-red-500",
        borderColor: "border-red-200 dark:border-red-800",
        rowHover: "hover:bg-red-50 dark:hover:bg-red-950/30",
      },
      hold: {
        title: "Hold Positions",
        emoji: "⚪",
        headerBg: "bg-gray-400",
        borderColor: "border-gray-200 dark:border-gray-700",
        rowHover: "hover:bg-gray-50 dark:hover:bg-gray-900/30",
      },
    };

    const c = config[actionType];
    const actionLabel =
      actionType === "buy" ? "Buy" : actionType === "sell" ? "Sell" : "Adjust";

    return (
      <div className="mb-4">
        <div
          className={`${c.headerBg} text-white px-4 py-2 rounded-t-lg font-semibold flex items-center gap-2`}
        >
          <span>{c.emoji}</span>
          <span>
            {c.title} ({items.length})
          </span>
        </div>
        <div
          className={`border ${c.borderColor} border-t-0 rounded-b-lg overflow-hidden`}
        >
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="h-10 px-3 text-left font-medium w-28">Symbol</th>
                <th className="h-10 px-3 text-left font-medium">Name</th>
                <th className="h-10 px-3 text-center font-medium w-16">Type</th>
                <th className="h-10 px-3 text-right font-medium w-24">
                  Ref Price
                </th>
                <th className="h-10 px-3 text-right font-medium w-20">
                  {actionLabel} Lots
                </th>
                <th className="h-10 px-3 text-right font-medium w-24">
                  {actionLabel} Shares
                </th>
                <th className="h-10 px-3 text-right font-medium w-28">
                  Target Value
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr
                  key={item.symbol || index}
                  className={`border-t border-gray-100 dark:border-gray-800 ${c.rowHover}`}
                >
                  <td className="px-3 py-3 font-mono font-bold text-base">
                    {item.symbol}
                  </td>
                  <td className="px-3 py-3">{item.name}</td>
                  <td className="px-3 py-3 text-center">
                    <Badge
                      variant="outline"
                      className={
                        item.type === "etf"
                          ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                          : ""
                      }
                    >
                      {item.type === "etf" ? "ETF" : "Stock"}
                    </Badge>
                  </td>
                  <td className="px-3 py-3 text-right font-medium text-base">
                    ¥{(item.reference_price || 0).toFixed(3)}
                  </td>
                  <td className="px-3 py-3 text-right font-bold text-lg">
                    {(item.action_lots || 0).toLocaleString()}
                  </td>
                  <td className="px-3 py-3 text-right text-muted-foreground">
                    {(item.action_shares || 0).toLocaleString()}
                  </td>
                  <td className="px-3 py-3 text-right">
                    ¥{(item.target_value || 0).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <Card className="border-orange-200 dark:border-orange-900">
      <CardHeader className="pb-3 bg-orange-50/50 dark:bg-orange-950/20">
        <CardTitle className="text-lg flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-orange-600" />
          Trading Orders
        </CardTitle>
        <CardDescription>
          {hasOrders
            ? `${buyPositions.length} buy, ${sellPositions.length} sell, ${holdPositions.length} hold`
            : "No trading orders - all positions are held"}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        {hasOrders ? (
          <>
            {renderActionTable(buyPositions, "buy")}
            {renderActionTable(sellPositions, "sell")}
            {holdPositions.length > 0 &&
              renderActionTable(holdPositions, "hold")}
          </>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <div className="text-4xl mb-2">✅</div>
            <p className="font-medium">No Trading Required</p>
            <p className="text-sm">
              All {holdPositions.length} positions are held with no changes
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const Route = createFileRoute("/_layout/target-portfolio")({
  component: TargetPortfolioPage,
  head: () => ({
    meta: [{ title: "Target Portfolio - QuantBot" }],
  }),
});

function TargetPortfolioPage() {
  const queryClient = useQueryClient();
  const [newEmail, setNewEmail] = useState("");
  const [portfolioSearch, setPortfolioSearch] = useState("");
  const [portfolioPage, setPortfolioPage] = useState(0);
  const portfolioPageSize = 50;

  // Fetch latest portfolio from API (reads from file, has correct current_shares)
  const {
    data: latestPortfolio,
    isLoading: portfolioLoading,
    error: portfolioError,
  } = useQuery({
    queryKey: ["latestPortfolio"],
    queryFn: fetchLatestPortfolio,
    refetchOnWindowFocus: true,
    staleTime: 30000, // 30 seconds
  });

  // Build routine result from API data
  const lastRoutineResult: RoutineResult | null = useMemo(() => {
    if (!latestPortfolio?.success) return null;
    return {
      success: true,
      generated_at: latestPortfolio.generated_at,
      trade_date: latestPortfolio.trade_date,
      signal_for_date: latestPortfolio.signal_for_date,
      total_value: latestPortfolio.total_value,
      weights: latestPortfolio.weights,
      target_portfolio: latestPortfolio.positions,
      portfolio_summary: latestPortfolio.summary,
      strategy: "etf_enhanced_indexing",
    };
  }, [latestPortfolio]);

  // Always use ETF Enhanced Indexing format (legacy format removed)
  const isETFStrategy = true;

  // Filter and paginate portfolio - only show positions with holdings (target_shares > 0)
  const filteredPortfolio = useMemo(() => {
    const portfolio = lastRoutineResult?.target_portfolio || [];
    // First filter to only include positions with target_shares > 0
    const holdingsOnly = portfolio.filter(
      (item: any) => (item.target_shares || 0) > 0,
    );
    if (!portfolioSearch.trim()) return holdingsOnly;
    const search = portfolioSearch.toLowerCase();
    return holdingsOnly.filter((item: any) => {
      // Support both new (symbol) and legacy (instrument) formats
      const code = item.symbol || item.instrument || "";
      const name = item.name || "";
      return (
        code.toLowerCase().includes(search) ||
        name.toLowerCase().includes(search)
      );
    });
  }, [lastRoutineResult?.target_portfolio, portfolioSearch]);

  const paginatedPortfolio = useMemo(() => {
    const start = portfolioPage * portfolioPageSize;
    return filteredPortfolio.slice(start, start + portfolioPageSize);
  }, [filteredPortfolio, portfolioPage]);

  const totalPages = Math.ceil(filteredPortfolio.length / portfolioPageSize);

  // Query for notification config
  const {
    data: configData,
    isLoading: configLoading,
    error: configError,
  } = useQuery({
    queryKey: ["notificationConfig"],
    queryFn: fetchNotificationConfig,
  });

  // Mutation for updating config
  const updateConfigMutation = useMutation({
    mutationFn: updateNotificationConfig,
    onSuccess: (response) => {
      if (response.success) {
        toast.success("Configuration updated");
        queryClient.invalidateQueries({ queryKey: ["notificationConfig"] });
      } else {
        toast.error(response.error || "Failed to update configuration");
      }
    },
    onError: (error) => {
      toast.error(`Failed to update configuration: ${error.message}`);
    },
  });

  // Mutation for adding recipient
  const addRecipientMutation = useMutation({
    mutationFn: addRecipient,
    onSuccess: (response) => {
      if (response.success) {
        toast.success("Recipient added");
        setNewEmail("");
        queryClient.invalidateQueries({ queryKey: ["notificationConfig"] });
      } else {
        toast.error(response.error || "Failed to add recipient");
      }
    },
    onError: (error) => {
      toast.error(`Failed to add recipient: ${error.message}`);
    },
  });

  // Mutation for removing recipient
  const removeRecipientMutation = useMutation({
    mutationFn: removeRecipient,
    onSuccess: (response) => {
      if (response.success) {
        toast.success("Recipient removed");
        queryClient.invalidateQueries({ queryKey: ["notificationConfig"] });
      } else {
        toast.error(response.error || "Failed to remove recipient");
      }
    },
    onError: (error) => {
      toast.error(`Failed to remove recipient: ${error.message}`);
    },
  });

  // Mutation for sending test email
  const sendTestMutation = useMutation({
    mutationFn: sendTestEmail,
    onSuccess: (response) => {
      if (response.success) {
        toast.success(response.message || "Test email sent");
      } else {
        toast.error(response.error || "Failed to send test email");
      }
    },
    onError: (error) => {
      toast.error(`Failed to send test email: ${error.message}`);
    },
  });

  const config = configData?.config;
  const isEnabled = config?.enabled ?? false;
  const recipients = config?.recipients ?? [];

  const handleToggleEnabled = () => {
    updateConfigMutation.mutate({ enabled: !isEnabled });
  };

  const handleAddRecipient = (e: React.FormEvent) => {
    e.preventDefault();
    if (newEmail.trim() && newEmail.includes("@")) {
      addRecipientMutation.mutate(newEmail.trim());
    } else {
      toast.error("Please enter a valid email address");
    }
  };

  const handleRemoveRecipient = (email: string) => {
    removeRecipientMutation.mutate(email);
  };

  const handleSendTest = () => {
    if (recipients.length === 0) {
      toast.error("Please add at least one recipient first");
      return;
    }
    sendTestMutation.mutate(undefined);
  };

  const handleExportJson = () => {
    const portfolio = lastRoutineResult?.target_portfolio || [];
    const summary = lastRoutineResult?.portfolio_summary || {};
    const weights = lastRoutineResult?.weights;

    // Export in appropriate format based on strategy
    const exportData = isETFStrategy
      ? {
          generated_at:
            lastRoutineResult?.generated_at || new Date().toISOString(),
          trade_date: lastRoutineResult?.trade_date || "",
          signal_for_date: lastRoutineResult?.signal_for_date || "",
          total_value: lastRoutineResult?.total_value || 1000000,
          region: lastRoutineResult?.region || "cn",
          lot_size: lastRoutineResult?.lot_size || 100,
          weights: weights,
          positions: portfolio,
          summary: summary,
        }
      : {
          generated_at: new Date().toISOString(),
          target_date: (summary as any).target_date,
          benchmark: (summary as any).benchmark_name,
          total_stocks: (summary as any).total_stocks,
          portfolio: portfolio,
        };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const dateStr =
      lastRoutineResult?.signal_for_date ||
      (summary as any).target_date ||
      "export";
    a.download = `target_portfolio_${dateStr}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Portfolio exported successfully");
  };

  const portfolioSummary = lastRoutineResult?.portfolio_summary;
  const hasPortfolio =
    lastRoutineResult?.target_portfolio &&
    lastRoutineResult.target_portfolio.length > 0;

  // Show loading state
  if (portfolioLoading) {
    return (
      <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
        <div className="h-full overflow-y-auto p-6 md:p-8">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">
              Loading portfolio...
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (portfolioError) {
    return (
      <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
        <div className="h-full overflow-y-auto p-6 md:p-8">
          <div className="flex items-center justify-center h-64">
            <XCircle className="h-8 w-8 text-red-500" />
            <span className="ml-2 text-red-500">
              Failed to load portfolio: {portfolioError.message}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Target Portfolio</h1>
              <p className="text-muted-foreground">
                View target portfolio and configure email notifications
              </p>
            </div>
            {hasPortfolio && (
              <Button variant="outline" onClick={handleExportJson}>
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            )}
          </div>

          {/* Portfolio Summary - Green theme */}
          {lastRoutineResult && (
            <Card className="border-green-200 dark:border-green-900">
              <CardHeader className="pb-3 bg-green-50/50 dark:bg-green-950/20">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-green-600" />
                    Portfolio Summary
                  </CardTitle>
                  <Badge className="bg-green-500">
                    Signal: {lastRoutineResult?.signal_for_date || "N/A"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {/* Key Info Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
                    <div className="text-xs text-green-600/80 uppercase tracking-wide">
                      Trade Date
                    </div>
                    <div className="text-lg font-semibold text-green-700 dark:text-green-400">
                      {lastRoutineResult?.trade_date || "-"}
                    </div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
                    <div className="text-xs text-green-600/80 uppercase tracking-wide">
                      Total Value
                    </div>
                    <div className="text-lg font-semibold text-green-700 dark:text-green-400">
                      ¥{(lastRoutineResult?.total_value || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
                    <div className="text-xs text-green-600/80 uppercase tracking-wide">
                      Region
                    </div>
                    <div className="text-lg font-semibold text-green-700 dark:text-green-400">
                      {(lastRoutineResult?.region || "cn").toUpperCase()}
                    </div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
                    <div className="text-xs text-green-600/80 uppercase tracking-wide">
                      Lot Size
                    </div>
                    <div className="text-lg font-semibold text-green-700 dark:text-green-400">
                      {lastRoutineResult?.lot_size || 100}
                    </div>
                  </div>
                </div>

                {/* Weights Section */}
                {lastRoutineResult?.weights && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 rounded-lg p-3">
                      <div className="text-xs text-emerald-600/80 uppercase tracking-wide">
                        ETF Weight
                      </div>
                      <div className="text-xl font-bold text-emerald-600">
                        {(
                          (lastRoutineResult.weights.etf_weight || 0) * 100
                        ).toFixed(0)}
                        %
                      </div>
                    </div>
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 rounded-lg p-3">
                      <div className="text-xs text-emerald-600/80 uppercase tracking-wide">
                        Alpha Weight
                      </div>
                      <div className="text-xl font-bold text-emerald-600">
                        {(
                          (lastRoutineResult.weights.alpha_weight || 0) * 100
                        ).toFixed(0)}
                        %
                      </div>
                    </div>
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 rounded-lg p-3">
                      <div className="text-xs text-emerald-600/80 uppercase tracking-wide">
                        Score Spread
                      </div>
                      <div className="text-xl font-bold text-emerald-600">
                        {(lastRoutineResult.weights.score_spread || 0).toFixed(
                          4,
                        )}
                      </div>
                    </div>
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 rounded-lg p-3">
                      <div className="text-xs text-emerald-600/80 uppercase tracking-wide">
                        Weight Mode
                      </div>
                      <div className="text-xl font-bold text-emerald-600 capitalize">
                        {lastRoutineResult.weights.weight_mode || "dynamic"}
                      </div>
                    </div>
                  </div>
                )}

                {/* Position Counts */}
                {portfolioSummary && (
                  <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                    <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-blue-600">
                        {portfolioSummary.etf_positions || 0}
                      </div>
                      <div className="text-xs text-blue-600/80">ETF</div>
                    </div>
                    <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-purple-600">
                        {portfolioSummary.stock_positions || 0}
                      </div>
                      <div className="text-xs text-purple-600/80">Stocks</div>
                    </div>
                    <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold">
                        {portfolioSummary.total_positions || 0}
                      </div>
                      <div className="text-xs text-muted-foreground">Total</div>
                    </div>
                    <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-green-600">
                        {portfolioSummary.buy_count || 0}
                      </div>
                      <div className="text-xs text-green-600/80">Buy</div>
                    </div>
                    <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-red-600">
                        {portfolioSummary.sell_count || 0}
                      </div>
                      <div className="text-xs text-red-600/80">Sell</div>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-2 text-center">
                      <div className="text-xl font-bold text-gray-500">
                        {portfolioSummary.hold_count || 0}
                      </div>
                      <div className="text-xs text-gray-500">Hold</div>
                    </div>
                  </div>
                )}

                {/* Generated At */}
                <div className="text-xs text-muted-foreground text-right">
                  Generated:{" "}
                  {lastRoutineResult?.generated_at
                    ? new Date(lastRoutineResult.generated_at).toLocaleString()
                    : "-"}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trading Orders Section - Split by action type */}
          {hasPortfolio && (
            <TradingOrdersSection
              positions={lastRoutineResult?.target_portfolio || []}
            />
          )}

          {/* Full Holdings Table */}
          {hasPortfolio ? (
            <Card className="border-blue-200 dark:border-blue-900">
              <CardHeader className="pb-3 bg-blue-50/50 dark:bg-blue-950/20">
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                  Full Holdings Detail
                </CardTitle>
                <CardDescription>
                  Complete portfolio with {filteredPortfolio.length} positions
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4">
                {/* Search */}
                <div className="flex items-center justify-between mb-4">
                  <Input
                    placeholder="Search symbol or name..."
                    value={portfolioSearch}
                    onChange={(e) => {
                      setPortfolioSearch(e.target.value);
                      setPortfolioPage(0);
                    }}
                    className="max-w-xs border-blue-200 focus:border-blue-400"
                  />
                </div>

                {/* Portfolio table - Shows holdings AFTER executing orders */}
                <div className="rounded-lg border border-blue-200 dark:border-blue-900 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm table-fixed">
                      <thead className="bg-blue-50 dark:bg-blue-950/50 border-b border-blue-200 dark:border-blue-900">
                        <tr>
                          <th className="h-11 px-2 text-center font-semibold text-blue-800 dark:text-blue-300 w-12">
                            Rank
                          </th>
                          <th className="h-11 px-2 text-left font-semibold text-blue-800 dark:text-blue-300 w-24">
                            Symbol
                          </th>
                          <th className="h-11 px-2 text-left font-semibold text-blue-800 dark:text-blue-300 w-24">
                            Name
                          </th>
                          <th className="h-11 px-2 text-center font-semibold text-blue-800 dark:text-blue-300 w-16">
                            Type
                          </th>
                          <th className="h-11 px-2 text-right font-semibold text-blue-800 dark:text-blue-300 w-16">
                            Weight
                          </th>
                          <th className="h-11 px-2 text-right font-semibold text-blue-800 dark:text-blue-300 w-16">
                            Score
                          </th>
                          <th className="h-11 px-2 text-right font-semibold text-blue-800 dark:text-blue-300 w-20">
                            Price
                          </th>
                          <th className="h-11 px-2 text-right font-semibold text-blue-800 dark:text-blue-300 w-20">
                            Shares
                          </th>
                          <th className="h-11 px-2 text-right font-semibold text-blue-800 dark:text-blue-300 w-24">
                            Value
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedPortfolio.map((item: any, index: number) => (
                          <tr
                            key={item.symbol || index}
                            className={`border-b border-blue-100 dark:border-blue-900/50 hover:bg-blue-50/50 dark:hover:bg-blue-950/30 ${item.type === "etf" ? "bg-emerald-50/50 dark:bg-emerald-950/20" : ""}`}
                          >
                            <td className="px-2 py-2 text-center font-medium text-blue-700 dark:text-blue-400">
                              {item.rank}
                            </td>
                            <td className="px-2 py-2 font-mono font-semibold truncate">
                              {item.symbol}
                            </td>
                            <td
                              className="px-2 py-2 truncate"
                              title={item.name}
                            >
                              {item.name}
                            </td>
                            <td className="px-2 py-2 text-center">
                              <Badge
                                className={
                                  item.type === "etf"
                                    ? "bg-emerald-500"
                                    : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
                                }
                              >
                                {item.type?.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="px-2 py-2 text-right font-medium">
                              {((item.weight || 0) * 100).toFixed(1)}%
                            </td>
                            <td className="px-2 py-2 text-right text-muted-foreground">
                              {item.score != null ? item.score.toFixed(4) : "-"}
                            </td>
                            <td className="px-2 py-2 text-right font-medium">
                              ¥{(item.reference_price || 0).toFixed(2)}
                            </td>
                            <td className="px-2 py-2 text-right font-medium">
                              {(item.target_shares || 0).toLocaleString()}
                            </td>
                            <td className="px-2 py-2 text-right">
                              ¥{(item.target_value || 0).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setPortfolioPage((p) => Math.max(0, p - 1))
                      }
                      disabled={portfolioPage === 0}
                    >
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Page {portfolioPage + 1} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setPortfolioPage((p) => Math.min(totalPages - 1, p + 1))
                      }
                      disabled={portfolioPage >= totalPages - 1}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-muted-foreground">
                  <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-30" />
                  <p className="text-lg font-medium">No Portfolio Data</p>
                  <p className="text-sm mt-1">
                    Run a routine from the Routine page to generate target
                    portfolio
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Email Notification Settings */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-blue-500" />
                  <CardTitle className="text-lg">Email Notifications</CardTitle>
                </div>
                {configLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : isEnabled ? (
                  <Badge className="bg-green-500">Enabled</Badge>
                ) : (
                  <Badge variant="secondary">Disabled</Badge>
                )}
              </div>
              <CardDescription>
                Receive daily trading reports via email after each routine
                execution
              </CardDescription>
            </CardHeader>
            <CardContent>
              {configError ? (
                <div className="flex items-center gap-2 text-red-500">
                  <XCircle className="h-4 w-4" />
                  <span>Failed to load configuration</span>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={isEnabled}
                      onCheckedChange={handleToggleEnabled}
                      disabled={updateConfigMutation.isPending}
                    />
                    <Label>
                      {isEnabled
                        ? "Notifications are enabled"
                        : "Notifications are disabled"}
                    </Label>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSendTest}
                    disabled={
                      sendTestMutation.isPending ||
                      !isEnabled ||
                      recipients.length === 0
                    }
                  >
                    {sendTestMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Send Test Email
                      </>
                    )}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recipients Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-purple-500" />
                <CardTitle className="text-lg">Email Recipients</CardTitle>
              </div>
              <CardDescription>
                Add email addresses to receive trading reports
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add recipient form */}
              <form onSubmit={handleAddRecipient} className="flex gap-2">
                <Input
                  type="email"
                  placeholder="Enter email address..."
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="submit"
                  disabled={addRecipientMutation.isPending || !newEmail.trim()}
                >
                  {addRecipientMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-1" />
                      Add
                    </>
                  )}
                </Button>
              </form>

              {/* Recipients list */}
              {recipients.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  <Mail className="h-6 w-6 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No recipients configured</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {recipients.map((email: string) => (
                    <div
                      key={email}
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                    >
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <span>{email}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveRecipient(email)}
                        disabled={removeRecipientMutation.isPending}
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* SMTP Info Card */}
          <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
            <CardContent className="pt-6">
              <div className="flex gap-3">
                <Settings className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-blue-700 dark:text-blue-400">
                    SMTP Configuration
                  </p>
                  <p className="text-blue-600 dark:text-blue-300 mt-1">
                    SMTP settings are configured via environment variables in
                    the .env file. Current configuration:
                  </p>
                  {config && (
                    <div className="grid grid-cols-2 gap-2 mt-2 text-blue-600 dark:text-blue-300">
                      <span>Host: {config.smtp_host || "Not set"}</span>
                      <span>Port: {config.smtp_port || "Not set"}</span>
                      <span>From: {config.from_email || "Not set"}</span>
                      <span>TLS: {config.smtp_tls ? "Yes" : "No"}</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
