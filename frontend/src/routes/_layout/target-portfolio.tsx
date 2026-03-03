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

// Types
interface PortfolioItem {
  rank: number;
  instrument: string;
  benchmark_weight: number;
  score: number;
  target_weight: number;
  deviation: number;
  deviation_pct: string;
  action: string;
}

interface PortfolioSummary {
  benchmark: string;
  benchmark_name: string;
  total_stocks: number;
  overweight_count: number;
  underweight_count: number;
  neutral_count: number;
  max_deviation: number;
  generated_at: string;
  target_date: string;
}

interface RoutineResult {
  success: boolean;
  cur_time?: string;
  executed_at?: string;
  total_duration_seconds?: number;
  signal_count?: number;
  error?: string;
  target_portfolio?: PortfolioItem[];
  portfolio_summary?: PortfolioSummary;
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

  // Filter and paginate portfolio
  const filteredPortfolio = useMemo(() => {
    const portfolio = lastRoutineResult?.target_portfolio || [];
    if (!portfolioSearch.trim()) return portfolio;
    const search = portfolioSearch.toLowerCase();
    return portfolio.filter((item) =>
      item.instrument.toLowerCase().includes(search),
    );
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
    const summary: any = lastRoutineResult?.portfolio_summary || {};
    const exportData = {
      generated_at: new Date().toISOString(),
      target_date: summary.target_date,
      benchmark: summary.benchmark_name,
      total_stocks: summary.total_stocks,
      portfolio: portfolio.map((item: PortfolioItem) => ({
        rank: item.rank,
        instrument: item.instrument,
        score: item.score,
        benchmark_weight: item.benchmark_weight,
        target_weight: item.target_weight,
        deviation: item.deviation,
        action: item.action,
      })),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `target_portfolio_${summary.target_date || "export"}.json`;
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

          {/* Portfolio Summary */}
          {portfolioSummary && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Portfolio Summary</CardTitle>
                  <Badge variant="outline">
                    {portfolioSummary.target_date}
                  </Badge>
                </div>
                <CardDescription>
                  {portfolioSummary.benchmark_name || "Enhanced Indexing"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-muted/50 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold">
                      {portfolioSummary.total_stocks}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Total Stocks
                    </div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {portfolioSummary.overweight_count}
                    </div>
                    <div className="text-sm text-green-600/80">Overweight</div>
                  </div>
                  <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-red-600">
                      {portfolioSummary.underweight_count}
                    </div>
                    <div className="text-sm text-red-600/80">Underweight</div>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-muted-foreground">
                      {portfolioSummary.neutral_count}
                    </div>
                    <div className="text-sm text-muted-foreground">Neutral</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Portfolio Table */}
          {hasPortfolio ? (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Portfolio Holdings</CardTitle>
                <CardDescription>
                  Target weights and deviations from benchmark
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Search and pagination controls */}
                <div className="flex items-center justify-between mb-4">
                  <Input
                    placeholder="Search by stock code..."
                    value={portfolioSearch}
                    onChange={(e) => {
                      setPortfolioSearch(e.target.value);
                      setPortfolioPage(0);
                    }}
                    className="max-w-xs"
                  />
                  <div className="text-sm text-muted-foreground">
                    Showing {paginatedPortfolio.length} of{" "}
                    {filteredPortfolio.length} stocks
                  </div>
                </div>

                {/* Portfolio table with sticky header */}
                <div className="rounded-md border max-h-[400px] overflow-y-auto">
                  <table className="w-full caption-bottom text-sm">
                    <thead className="sticky top-0 bg-background z-10 border-b">
                      <tr>
                        <th className="h-11 px-4 text-center align-middle text-xs font-semibold uppercase tracking-wider w-16">
                          Rank
                        </th>
                        <th className="h-11 px-4 text-left align-middle text-xs font-semibold uppercase tracking-wider">
                          Stock
                        </th>
                        <th className="h-11 px-4 text-right align-middle text-xs font-semibold uppercase tracking-wider">
                          Benchmark
                        </th>
                        <th className="h-11 px-4 text-right align-middle text-xs font-semibold uppercase tracking-wider">
                          Score
                        </th>
                        <th className="h-11 px-4 text-right align-middle text-xs font-semibold uppercase tracking-wider">
                          Target
                        </th>
                        <th className="h-11 px-4 text-right align-middle text-xs font-semibold uppercase tracking-wider">
                          Deviation
                        </th>
                        <th className="h-11 px-4 text-center align-middle text-xs font-semibold uppercase tracking-wider">
                          Action
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedPortfolio.map((item) => (
                        <tr
                          key={item.instrument}
                          className="border-b hover:bg-muted/50"
                        >
                          <td className="px-4 py-3 text-center font-medium">
                            {item.rank}
                          </td>
                          <td className="px-4 py-3 font-mono">
                            {item.instrument}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {(item.benchmark_weight * 100).toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-right">
                            {item.score.toFixed(4)}
                          </td>
                          <td className="px-4 py-3 text-right font-medium">
                            {(item.target_weight * 100).toFixed(2)}%
                          </td>
                          <td
                            className={`px-4 py-3 text-right ${
                              item.action === "超配"
                                ? "text-green-600"
                                : item.action === "低配"
                                  ? "text-red-600"
                                  : ""
                            }`}
                          >
                            {item.deviation_pct}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge
                              variant={
                                item.action === "超配"
                                  ? "default"
                                  : item.action === "低配"
                                    ? "destructive"
                                    : "secondary"
                              }
                              className={
                                item.action === "超配" ? "bg-green-500" : ""
                              }
                            >
                              {item.action}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
