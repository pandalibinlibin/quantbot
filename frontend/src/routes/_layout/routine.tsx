import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  Loader2,
  Play,
  Calendar,
  Activity,
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
import { OpenAPI } from "@/client";
import { toast } from "sonner";
import { useState, useEffect } from "react";

// API helper functions
async function fetchOnlineStatus() {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/online/status`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  if (!response.ok) {
    throw new Error("Failed to fetch online status");
  }
  return response.json();
}

async function executeRoutine() {
  console.log("Executing routine API call...");
  console.log("API Base URL:", OpenAPI.BASE);
  console.log(
    "Access Token:",
    localStorage.getItem("access_token") ? "Present" : "Missing",
  );

  const response = await fetch(`${OpenAPI.BASE}/api/v1/online/routine`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      "Content-Type": "application/json",
    },
  });

  console.log("Response status:", response.status);
  console.log("Response ok:", response.ok);

  if (!response.ok) {
    const errorText = await response.text();
    console.error("API Error:", errorText);
    throw new Error(
      `Failed to execute routine: ${response.status} - ${errorText}`,
    );
  }

  const result = await response.json();
  console.log("Routine result:", result);
  return result;
}

// Types
interface DataRange {
  start_date: string;
  end_date: string;
}

interface StatusResponse {
  is_initialized: boolean;
  freq: string;
  last_routine_time?: string;
  initialization_error?: string;
  config: Record<string, unknown>;
  data_range?: DataRange;
  signal_count?: number;
}

interface StepResult {
  step: string;
  success: boolean;
  duration_seconds: number;
  details?: Record<string, unknown>;
  error?: string;
}

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
  steps?: StepResult[];
  total_duration_seconds?: number;
  signal_count?: number;
  error?: string;
  target_portfolio?: PortfolioItem[];
  portfolio_summary?: PortfolioSummary;
}

const ROUTINE_RESULT_KEY = "quantbot_last_routine_result";

function RoutinePage() {
  const queryClient = useQueryClient();
  const [lastRoutineResult, setLastRoutineResult] =
    useState<RoutineResult | null>(() => {
      // Load from localStorage on initial render
      try {
        const saved = localStorage.getItem(ROUTINE_RESULT_KEY);
        return saved ? JSON.parse(saved) : null;
      } catch {
        return null;
      }
    });
  // Save to localStorage when result changes
  useEffect(() => {
    if (lastRoutineResult) {
      localStorage.setItem(
        ROUTINE_RESULT_KEY,
        JSON.stringify(lastRoutineResult),
      );
    }
  }, [lastRoutineResult]);

  // Fetch online status
  const {
    data: status,
    isLoading: statusLoading,
    error: statusError,
  } = useQuery<StatusResponse>({
    queryKey: ["onlineStatus"],
    queryFn: fetchOnlineStatus,
    refetchInterval: 10000,
  });

  // Execute routine mutation
  const routineMutation = useMutation<RoutineResult>({
    mutationFn: executeRoutine,
    onSuccess: (data) => {
      setLastRoutineResult(data);
      if (data.success) {
        toast.success("Routine executed successfully", {
          description: `Duration: ${data.total_duration_seconds?.toFixed(1)}s, Signals: ${data.signal_count || 0}`,
        });
        queryClient.invalidateQueries({ queryKey: ["onlineStatus"] });
      } else {
        toast.error("Routine execution failed", {
          description: data.error || "Unknown error",
        });
      }
    },
    onError: (error) => {
      toast.error("Failed to execute routine", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    },
  });

  const handleRunRoutine = () => {
    routineMutation.mutate();
  };

  const formatDateTime = (isoString?: string) => {
    if (!isoString) return "-";
    try {
      return new Date(isoString).toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  const getStepIcon = (step: string) => {
    // Match new readable step names from backend
    const stepLower = step.toLowerCase();
    if (stepLower.includes("data")) {
      return <Database className="h-4 w-4" />;
    } else if (stepLower.includes("model") || stepLower.includes("training")) {
      return <Activity className="h-4 w-4" />;
    } else if (
      stepLower.includes("signal") ||
      stepLower.includes("portfolio")
    ) {
      return <RefreshCw className="h-4 w-4" />;
    } else {
      return <Clock className="h-4 w-4" />;
    }
  };

  const getStepName = (step: string) => {
    // Backend now returns readable step names directly
    return step;
  };

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Routine</h1>
              <p className="text-muted-foreground">
                Daily routine execution and status monitoring
              </p>
            </div>
            <Button
              onClick={handleRunRoutine}
              disabled={routineMutation.isPending}
              size="lg"
            >
              {routineMutation.isPending ? (
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              ) : (
                <Play className="mr-2 h-5 w-5" />
              )}
              Run Routine
            </Button>
          </div>

          {/* Status Overview */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Status</CardTitle>
                {status?.is_initialized ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {statusLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin" />
                  ) : status?.is_initialized ? (
                    <Badge variant="default" className="bg-green-500">
                      Initialized
                    </Badge>
                  ) : (
                    <Badge variant="destructive">Not Initialized</Badge>
                  )}
                </div>
                {status?.initialization_error && (
                  <p className="text-xs text-destructive mt-1">
                    {status.initialization_error}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Last Executed
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold">
                  {statusLoading
                    ? "-"
                    : formatDateTime(status?.last_routine_time)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Data Range
                </CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold">
                  {statusLoading
                    ? "-"
                    : status?.data_range
                      ? `${status.data_range.start_date} ~ ${status.data_range.end_date}`
                      : "N/A"}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Portfolio Stocks
                </CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(
                    (
                      lastRoutineResult?.portfolio_summary as unknown as
                        | Record<string, number>
                        | undefined
                    )?.total_positions ||
                    (
                      lastRoutineResult?.portfolio_summary as unknown as
                        | Record<string, number>
                        | undefined
                    )?.total_stocks ||
                    (
                      lastRoutineResult?.portfolio_summary as unknown as
                        | Record<string, number>
                        | undefined
                    )?.position_count ||
                    0
                  ).toLocaleString()}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Error Display */}
          {statusError && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-destructive">Error</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-destructive">
                  {statusError instanceof Error
                    ? statusError.message
                    : "Failed to fetch status"}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Last Routine Result */}
          {lastRoutineResult && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {lastRoutineResult.success ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                      Last Routine Result
                    </CardTitle>
                    <CardDescription>
                      Executed at{" "}
                      {formatDateTime(lastRoutineResult.executed_at)} |
                      Duration:{" "}
                      {lastRoutineResult.total_duration_seconds?.toFixed(2)}s
                    </CardDescription>
                  </div>
                  {lastRoutineResult.signal_count !== undefined && (
                    <Badge variant="secondary">
                      {lastRoutineResult.signal_count} signals
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {lastRoutineResult.error ? (
                  <div className="p-4 bg-destructive/10 text-destructive rounded-md">
                    {lastRoutineResult.error}
                  </div>
                ) : lastRoutineResult.steps &&
                  lastRoutineResult.steps.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Step</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Duration</TableHead>
                        <TableHead>Details</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {lastRoutineResult.steps.map((step, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {getStepIcon(step.step)}
                              <span className="font-medium">
                                {getStepName(step.step)}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            {step.success ? (
                              <Badge variant="default" className="bg-green-500">
                                Success
                              </Badge>
                            ) : (
                              <Badge variant="destructive">Failed</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            {step.duration_seconds.toFixed(2)}s
                          </TableCell>
                          <TableCell className="max-w-md">
                            {step.error ? (
                              <span className="text-destructive">
                                {step.error}
                              </span>
                            ) : step.details ? (
                              <span className="text-muted-foreground text-sm">
                                {(step.details as { description?: string })
                                  .description ||
                                  JSON.stringify(step.details).substring(0, 80)}
                              </span>
                            ) : (
                              "-"
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <p className="text-muted-foreground">
                    No step details available
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Configuration</CardTitle>
              <CardDescription>
                Current online serving configuration
              </CardDescription>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : status?.config ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(status.config).map(([key, value]) => (
                    <div key={key} className="bg-muted/50 rounded-lg p-3">
                      <div className="text-sm text-muted-foreground">{key}</div>
                      <div
                        className="font-medium truncate"
                        title={String(value)}
                      >
                        {String(value) || "-"}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">
                  No configuration available
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/_layout/routine")({
  component: RoutinePage,
});
