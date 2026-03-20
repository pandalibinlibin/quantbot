import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Mail,
  Plus,
  Trash2,
  Send,
  XCircle,
  Loader2,
  Settings,
  Bell,
  Download,
  TrendingUp,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { OpenAPI } from "@/client";
import { toast } from "sonner";
import { useState, useEffect, useMemo } from "react";

// Types for ETF Enhanced Indexing Strategy
interface PortfolioPosition {
  rank: number;
  symbol: string;
  name: string;
  type: "etf" | "stock";
  weight: number;
  score?: number;
  target_value: number;
  reference_price: number;
  target_shares: number;
  current_shares: number;
  action: "buy" | "sell" | "hold";
  action_shares: number;
  action_lots: number;
}

interface PortfolioWeights {
  etf_weight: number;
  alpha_weight: number;
  score_spread: number;
  weight_mode: string;
}

interface PortfolioSummary {
  total_positions: number;
  etf_positions: number;
  stock_positions: number;
  buy_count: number;
  sell_count: number;
  hold_count: number;
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

// LocalStorage key for routine result
const ROUTINE_RESULT_KEY = "quantbot_last_routine_result";

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

  // Load last routine result from localStorage
  const [lastRoutineResult, setLastRoutineResult] =
    useState<RoutineResult | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(ROUTINE_RESULT_KEY);
    if (stored) {
      try {
        setLastRoutineResult(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse stored routine result:", e);
      }
    }
  }, []);

  // Always use ETF Enhanced Indexing format (legacy format removed)
  const isETFStrategy = true;

  // Filter and paginate portfolio
  const filteredPortfolio = useMemo(() => {
    const portfolio = lastRoutineResult?.target_portfolio || [];
    if (!portfolioSearch.trim()) return portfolio;
    const search = portfolioSearch.toLowerCase();
    return portfolio.filter((item: any) => {
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

          {/* Portfolio Holdings Table - Green theme */}
          {hasPortfolio ? (
            <Card className="border-green-200 dark:border-green-900">
              <CardHeader className="pb-3 bg-green-50/50 dark:bg-green-950/20">
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  Portfolio Holdings
                </CardTitle>
                <CardDescription>
                  All {filteredPortfolio.length} positions with trading actions
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
                    className="max-w-xs border-green-200 focus:border-green-400"
                  />
                </div>

                {/* Portfolio table */}
                <div className="rounded-lg border border-green-200 dark:border-green-900 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-green-50 dark:bg-green-950/50 border-b border-green-200 dark:border-green-900">
                        <tr>
                          <th className="h-11 px-3 text-center font-semibold text-green-800 dark:text-green-300 w-14">
                            Rank
                          </th>
                          <th className="h-11 px-3 text-left font-semibold text-green-800 dark:text-green-300 w-28">
                            Symbol
                          </th>
                          <th className="h-11 px-3 text-left font-semibold text-green-800 dark:text-green-300 min-w-[100px]">
                            Name
                          </th>
                          <th className="h-11 px-3 text-center font-semibold text-green-800 dark:text-green-300 w-16">
                            Type
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-20">
                            Weight
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-20">
                            Score
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-24">
                            Price
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-28">
                            Target Value
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-24">
                            Target Shares
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-24">
                            Current
                          </th>
                          <th className="h-11 px-3 text-center font-semibold text-green-800 dark:text-green-300 w-20">
                            Action
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-24">
                            Shares
                          </th>
                          <th className="h-11 px-3 text-right font-semibold text-green-800 dark:text-green-300 w-20">
                            Lots
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedPortfolio.map((item: any, index: number) => (
                          <tr
                            key={item.symbol || index}
                            className={`border-b border-green-100 dark:border-green-900/50 hover:bg-green-50/50 dark:hover:bg-green-950/30 ${item.type === "etf" ? "bg-emerald-50/50 dark:bg-emerald-950/20" : ""}`}
                          >
                            <td className="px-3 py-3 text-center font-medium text-green-700 dark:text-green-400">
                              {item.rank}
                            </td>
                            <td className="px-3 py-3 font-mono font-semibold">
                              {item.symbol}
                            </td>
                            <td
                              className="px-3 py-3 truncate"
                              title={item.name}
                            >
                              {item.name}
                            </td>
                            <td className="px-3 py-3 text-center">
                              <Badge
                                className={
                                  item.type === "etf"
                                    ? "bg-emerald-500"
                                    : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
                                }
                              >
                                {item.type?.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="px-3 py-3 text-right font-medium">
                              {((item.weight || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="px-3 py-3 text-right text-muted-foreground">
                              {item.score != null ? item.score.toFixed(4) : "-"}
                            </td>
                            <td className="px-3 py-3 text-right font-medium">
                              ¥{(item.reference_price || 0).toFixed(2)}
                            </td>
                            <td className="px-3 py-3 text-right">
                              ¥
                              {(item.target_value || 0).toLocaleString(
                                undefined,
                                {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                },
                              )}
                            </td>
                            <td className="px-3 py-3 text-right font-medium">
                              {(item.target_shares || 0).toLocaleString()}
                            </td>
                            <td className="px-3 py-3 text-right text-muted-foreground">
                              {(item.current_shares || 0).toLocaleString()}
                            </td>
                            <td className="px-3 py-3 text-center">
                              <Badge
                                className={`${
                                  item.action === "buy"
                                    ? "bg-green-500"
                                    : item.action === "sell"
                                      ? "bg-red-500"
                                      : "bg-gray-400"
                                }`}
                              >
                                {item.action?.toUpperCase()}
                              </Badge>
                            </td>
                            <td
                              className={`px-3 py-3 text-right font-medium ${item.action === "buy" ? "text-green-600" : item.action === "sell" ? "text-red-600" : ""}`}
                            >
                              {(item.action_shares || 0).toLocaleString()}
                            </td>
                            <td
                              className={`px-3 py-3 text-right ${item.action === "buy" ? "text-green-600" : item.action === "sell" ? "text-red-600" : ""}`}
                            >
                              {item.action_lots || 0}
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
