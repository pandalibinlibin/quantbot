import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  RefreshCw,
  TrendingUp,
  BarChart3,
  Target,
  Layers,
  Calendar,
  Activity,
  Info,
  AlertCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ModelsService } from "@/client";
import {
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

export const Route = createFileRoute("/_layout/models")({
  component: ModelsPage,
  head: () => ({ meta: [{ title: "Model - Qlib Quantbot" }] }),
});

// Helper function to format date
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}

// Helper function to format percentage
function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

// Helper function to get evaluation badge
function getEvaluationBadge(
  value: number,
  thresholds: { good: number; excellent: number; outstanding?: number },
  isHigherBetter: boolean = true,
): {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
} {
  const compare = isHigherBetter
    ? (v: number, t: number) => v >= t
    : (v: number, t: number) => v <= t;

  if (thresholds.outstanding && compare(value, thresholds.outstanding)) {
    return { label: "Outstanding", variant: "default" };
  }
  if (compare(value, thresholds.excellent)) {
    return { label: "Excellent", variant: "default" };
  }
  if (compare(value, thresholds.good)) {
    return { label: "Good", variant: "secondary" };
  }
  return { label: "Needs Improvement", variant: "outline" };
}

// Info tooltip component
function InfoTooltip({ content }: { content: string }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="text-sm">{content}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Metric card component
function MetricCard({
  label,
  value,
  format = "number",
  tooltip,
  evaluation,
}: {
  label: string;
  value: number;
  format?: "number" | "percent" | "ratio";
  tooltip?: string;
  evaluation?: {
    label: string;
    variant: "default" | "secondary" | "destructive" | "outline";
  };
}) {
  const formattedValue =
    format === "percent"
      ? formatPercent(value)
      : format === "ratio"
        ? value.toFixed(3)
        : value.toFixed(4);

  return (
    <div className="bg-muted/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm text-muted-foreground">{label}</span>
        {tooltip && <InfoTooltip content={tooltip} />}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-bold">{formattedValue}</span>
        {evaluation && (
          <Badge variant={evaluation.variant} className="text-xs">
            {evaluation.label}
          </Badge>
        )}
      </div>
    </div>
  );
}

function ModelsPage() {
  // Query for model metrics
  const {
    data: metricsData,
    isLoading: metricsLoading,
    error: metricsError,
  } = useQuery({
    queryKey: ["modelMetrics"],
    queryFn: () => ModelsService.getActiveModelMetrics(),
    retry: false,
  });

  // Query for IC series chart data
  const { data: icSeriesData } = useQuery({
    queryKey: ["icSeriesChart"],
    queryFn: () => ModelsService.getIcSeriesChart(),
    enabled: !!metricsData,
  });

  // Query for group returns chart data
  const { data: groupReturnsData } = useQuery({
    queryKey: ["groupReturnsChart"],
    queryFn: () => ModelsService.getGroupReturnsChart(),
    enabled: !!metricsData,
  });

  // Query for feature importance
  const { data: featureImportanceData } = useQuery({
    queryKey: ["featureImportance"],
    queryFn: () => ModelsService.getFeatureImportance({ limit: 20 }),
    enabled: !!metricsData,
  });

  // Loading state
  if (metricsLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)]">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Loading model metrics...</p>
      </div>
    );
  }

  // Error state - no metrics available
  if (metricsError || !metricsData) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)]">
        <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
        <h2 className="text-xl font-semibold mb-2">
          No Model Metrics Available
        </h2>
        <p className="text-muted-foreground text-center max-w-md">
          Model metrics have not been calculated yet. Please run the routine
          first to train models and generate metrics.
        </p>
        <p className="text-sm text-muted-foreground mt-4">
          Go to Online Serving → Execute Routine
        </p>
      </div>
    );
  }

  const {
    ic_metrics,
    long_short_metrics,
    quality_metrics,
    feature_importance,
  } = metricsData;

  // Prepare IC series chart data
  const icChartData = (() => {
    const rawData = icSeriesData?.data as Record<string, unknown> | undefined;
    const icData = rawData?.ic as
      | Array<{ datetime?: string; ic?: number }>
      | undefined;
    const rankIcData = rawData?.rank_ic as
      | Array<{ datetime?: string; rank_ic?: number; ic?: number }>
      | undefined;
    if (!icData) return [];
    return icData.map((item, index) => ({
      date: item.datetime?.substring(0, 10) || String(index),
      ic: item.ic ?? 0,
      rankIc: rankIcData?.[index]?.rank_ic ?? rankIcData?.[index]?.ic ?? 0,
    }));
  })();

  // Prepare feature importance chart data (top 20)
  const featureChartData = (featureImportanceData || feature_importance || [])
    .slice(0, 20)
    .map((item: any) => ({
      feature:
        item.feature?.length > 15
          ? item.feature.substring(0, 15) + "..."
          : item.feature,
      importance: item.importance,
    }));

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div>
            <h1 className="text-2xl font-bold">Model</h1>
            <p className="text-muted-foreground">
              Rolling Ensemble model performance analysis
            </p>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Model Type Card */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                    <Layers className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Model Type</p>
                    <p className="font-semibold">
                      LGBModel - {metricsData.model_type}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Last Updated Card */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                    <Calendar className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">
                      Last Updated
                    </p>
                    <p className="font-semibold">
                      {formatDate(metricsData.calculated_at)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* IC Card */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                    <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">IC Mean</p>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold">
                        {ic_metrics.ic_mean.toFixed(4)}
                      </p>
                      <Badge
                        variant={
                          getEvaluationBadge(ic_metrics.ic_mean, {
                            good: 0.03,
                            excellent: 0.05,
                            outstanding: 0.08,
                          }).variant
                        }
                        className="text-xs"
                      >
                        {
                          getEvaluationBadge(ic_metrics.ic_mean, {
                            good: 0.03,
                            excellent: 0.05,
                            outstanding: 0.08,
                          }).label
                        }
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Sharpe Card */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
                    <Activity className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">
                      Sharpe Ratio
                    </p>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold">
                        {long_short_metrics.long_short_ann_sharpe.toFixed(2)}
                      </p>
                      <Badge
                        variant={
                          getEvaluationBadge(
                            long_short_metrics.long_short_ann_sharpe,
                            { good: 1.0, excellent: 1.5, outstanding: 2.0 },
                          ).variant
                        }
                        className="text-xs"
                      >
                        {
                          getEvaluationBadge(
                            long_short_metrics.long_short_ann_sharpe,
                            { good: 1.0, excellent: 1.5, outstanding: 2.0 },
                          ).label
                        }
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* IC Analysis Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-purple-500" />
                <CardTitle>IC Analysis</CardTitle>
                <InfoTooltip content="Information Coefficient (IC) measures the correlation between model predictions and actual returns. Higher IC indicates better predictive power. ICIR measures the stability of IC over time." />
              </div>
              <CardDescription>
                Prediction-return correlation analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* IC Metrics - Row 1: Pearson IC */}
              <div className="mb-4">
                <h4 className="text-sm font-medium text-muted-foreground mb-3">
                  Pearson IC
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <MetricCard
                    label="IC Mean"
                    value={ic_metrics.ic_mean}
                    tooltip="Average Pearson correlation between predictions and returns"
                    evaluation={getEvaluationBadge(ic_metrics.ic_mean, {
                      good: 0.03,
                      excellent: 0.05,
                      outstanding: 0.08,
                    })}
                  />
                  <MetricCard
                    label="IC Std"
                    value={ic_metrics.ic_std}
                    tooltip="Standard deviation of IC - lower is more stable"
                  />
                  <MetricCard
                    label="ICIR"
                    value={ic_metrics.icir}
                    format="ratio"
                    tooltip="IC Information Ratio = IC Mean / IC Std. Higher indicates more stable predictions."
                    evaluation={getEvaluationBadge(ic_metrics.icir, {
                      good: 1.0,
                      excellent: 1.5,
                    })}
                  />
                </div>
              </div>
              {/* IC Metrics - Row 2: Rank IC */}
              <div className="mb-6">
                <h4 className="text-sm font-medium text-muted-foreground mb-3">
                  Rank IC (Spearman)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <MetricCard
                    label="Rank IC Mean"
                    value={ic_metrics.rank_ic_mean}
                    tooltip="Spearman rank correlation - more robust to outliers"
                    evaluation={getEvaluationBadge(ic_metrics.rank_ic_mean, {
                      good: 0.03,
                      excellent: 0.05,
                      outstanding: 0.08,
                    })}
                  />
                  <MetricCard
                    label="Rank IC Std"
                    value={ic_metrics.rank_ic_std}
                    tooltip="Standard deviation of Rank IC"
                  />
                  <MetricCard
                    label="Rank ICIR"
                    value={ic_metrics.rank_icir}
                    format="ratio"
                    tooltip="Rank IC Information Ratio"
                    evaluation={getEvaluationBadge(ic_metrics.rank_icir, {
                      good: 1.0,
                      excellent: 1.5,
                    })}
                  />
                </div>
              </div>

              {/* IC Time Series Chart */}
              {icChartData.length > 0 && (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={icChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        interval="preserveStartEnd"
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <RechartsTooltip />
                      <Legend />
                      <ReferenceLine
                        y={0}
                        stroke="#666"
                        strokeDasharray="3 3"
                      />
                      <Line
                        type="monotone"
                        dataKey="ic"
                        stroke="#8b5cf6"
                        name="IC"
                        dot={false}
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="rankIc"
                        stroke="#06b6d4"
                        name="Rank IC"
                        dot={false}
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Long-Short Performance Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-green-500" />
                <CardTitle>Long-Short Performance</CardTitle>
                <InfoTooltip content="Long-Short strategy: Long top 20% stocks (highest predicted returns), Short bottom 20% stocks (lowest predicted returns). This measures the model's ability to differentiate winners from losers." />
              </div>
              <CardDescription>
                Strategy performance based on model predictions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <MetricCard
                  label="Long-Short Return"
                  value={long_short_metrics.long_short_ann_return}
                  format="percent"
                  tooltip="Annualized return of long-short strategy"
                  evaluation={getEvaluationBadge(
                    long_short_metrics.long_short_ann_return,
                    { good: 0.1, excellent: 0.15 },
                  )}
                />
                <MetricCard
                  label="Long-Short Sharpe"
                  value={long_short_metrics.long_short_ann_sharpe}
                  format="ratio"
                  tooltip="Sharpe ratio = Return / Risk. Higher is better."
                  evaluation={getEvaluationBadge(
                    long_short_metrics.long_short_ann_sharpe,
                    { good: 1.0, excellent: 1.5, outstanding: 2.0 },
                  )}
                />
                <MetricCard
                  label="Long-Avg Return"
                  value={long_short_metrics.long_avg_ann_return}
                  format="percent"
                  tooltip="Long portfolio vs market average return"
                />
                <MetricCard
                  label="Long-Avg Sharpe"
                  value={long_short_metrics.long_avg_ann_sharpe}
                  format="ratio"
                  tooltip="Sharpe ratio of long-average strategy"
                />
              </div>

              {/* Evaluation Guide */}
              <div className="bg-muted/30 rounded-lg p-4 text-sm">
                <p className="font-medium mb-2">Evaluation Guide:</p>
                <ul className="grid grid-cols-2 md:grid-cols-4 gap-2 text-muted-foreground">
                  <li>• Return &gt; 10%: Good</li>
                  <li>• Return &gt; 15%: Excellent</li>
                  <li>• Sharpe &gt; 1.0: Acceptable</li>
                  <li>• Sharpe &gt; 2.0: Outstanding</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Prediction Quality Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Target className="h-5 w-5 text-blue-500" />
                <CardTitle>Prediction Quality</CardTitle>
                <InfoTooltip content="Measures the accuracy and stability of model predictions. Long Precision: accuracy of predicting up movements. Short Precision: accuracy of predicting down movements. Auto Correlation: prediction stability over time." />
              </div>
              <CardDescription>Accuracy and stability metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricCard
                  label="Long Precision"
                  value={quality_metrics.long_precision}
                  format="percent"
                  tooltip="Accuracy of predicting stocks that will go up"
                  evaluation={getEvaluationBadge(
                    quality_metrics.long_precision,
                    {
                      good: 0.55,
                      excellent: 0.6,
                    },
                  )}
                />
                <MetricCard
                  label="Short Precision"
                  value={quality_metrics.short_precision}
                  format="percent"
                  tooltip="Accuracy of predicting stocks that will go down"
                  evaluation={getEvaluationBadge(
                    quality_metrics.short_precision,
                    {
                      good: 0.55,
                      excellent: 0.6,
                    },
                  )}
                />
                <MetricCard
                  label="Auto Correlation"
                  value={quality_metrics.auto_correlation}
                  format="ratio"
                  tooltip="Prediction stability over time. Measures how similar today's predictions are to yesterday's. Values 0.3-0.7 indicate stable predictions. Too high (>0.9) may indicate overfitting or stale predictions."
                  evaluation={
                    quality_metrics.auto_correlation > 0.9
                      ? { label: "Too High", variant: "destructive" }
                      : quality_metrics.auto_correlation >= 0.3 &&
                          quality_metrics.auto_correlation <= 0.7
                        ? { label: "Good", variant: "default" }
                        : quality_metrics.auto_correlation >= 0.1
                          ? { label: "Acceptable", variant: "secondary" }
                          : { label: "Low", variant: "outline" }
                  }
                />
              </div>

              {/* Evaluation Guide */}
              <div className="bg-muted/30 rounded-lg p-4 text-sm mt-4">
                <p className="font-medium mb-2">Evaluation Guide:</p>
                <ul className="grid grid-cols-2 md:grid-cols-3 gap-2 text-muted-foreground">
                  <li>• Precision &gt; 55%: Good</li>
                  <li>• Precision &gt; 60%: Excellent</li>
                  <li>• Auto Corr 0.1-0.3: Normal</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Group Returns Card */}
          {groupReturnsData?.data &&
            Object.keys(groupReturnsData.data).length > 0 && (
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Layers className="h-5 w-5 text-cyan-500" />
                    <CardTitle>Group Returns Analysis</CardTitle>
                    <InfoTooltip content="Stocks are divided into 5 groups by prediction score. Group 1 has highest predicted returns, Group 5 has lowest. A good model should show clear separation between groups, with Group 1 outperforming Group 5." />
                  </div>
                  <CardDescription>
                    Cumulative returns by prediction quintile
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={(() => {
                          // Transform group returns data for chart
                          const groups = groupReturnsData.data as Record<
                            string,
                            Array<{
                              datetime: string;
                              cumulative_return: number;
                            }>
                          >;
                          const groupKeys = Object.keys(groups);
                          if (groupKeys.length === 0) return [];

                          // Get all dates from first group
                          const firstGroup = groups[groupKeys[0]] || [];
                          return firstGroup.map((item, idx) => {
                            const point: Record<string, any> = {
                              date: item.datetime?.substring(0, 10) || idx,
                            };
                            groupKeys.forEach((key) => {
                              point[key] =
                                groups[key]?.[idx]?.cumulative_return || 0;
                            });
                            return point;
                          });
                        })()}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 11 }}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tick={{ fontSize: 11 }}
                          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                        />
                        <RechartsTooltip
                          formatter={(value) =>
                            `${((value as number) * 100).toFixed(2)}%`
                          }
                        />
                        <Legend />
                        <ReferenceLine
                          y={0}
                          stroke="#666"
                          strokeDasharray="3 3"
                        />
                        <Line
                          type="monotone"
                          dataKey="Group1"
                          stroke="#22c55e"
                          name="Group 1 (Top)"
                          dot={false}
                          strokeWidth={2}
                        />
                        <Line
                          type="monotone"
                          dataKey="Group2"
                          stroke="#84cc16"
                          name="Group 2"
                          dot={false}
                          strokeWidth={1.5}
                        />
                        <Line
                          type="monotone"
                          dataKey="Group3"
                          stroke="#eab308"
                          name="Group 3"
                          dot={false}
                          strokeWidth={1.5}
                        />
                        <Line
                          type="monotone"
                          dataKey="Group4"
                          stroke="#f97316"
                          name="Group 4"
                          dot={false}
                          strokeWidth={1.5}
                        />
                        <Line
                          type="monotone"
                          dataKey="Group5"
                          stroke="#ef4444"
                          name="Group 5 (Bottom)"
                          dot={false}
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="bg-muted/30 rounded-lg p-4 text-sm mt-4">
                    <p className="font-medium mb-2">Interpretation:</p>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-muted-foreground">
                      <li>• Group 1 (Green) should have highest returns</li>
                      <li>• Group 5 (Red) should have lowest returns</li>
                      <li>
                        • Clear separation indicates good predictive power
                      </li>
                      <li>• Monotonic ordering is ideal</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            )}

          {/* Feature Importance Card */}
          {featureChartData.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-orange-500" />
                  <CardTitle>Feature Importance</CardTitle>
                  <InfoTooltip content="Shows which factors contribute most to the model's predictions. Based on the latest model in the Rolling Ensemble. Higher importance means the feature has more influence on predictions." />
                </div>
                <CardDescription>
                  Top 20 most important features from the latest model
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={featureChartData}
                      layout="vertical"
                      margin={{ left: 100 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tick={{ fontSize: 12 }} />
                      <YAxis
                        type="category"
                        dataKey="feature"
                        tick={{ fontSize: 11 }}
                        width={100}
                      />
                      <RechartsTooltip />
                      <Bar
                        dataKey="importance"
                        fill="#f97316"
                        name="Importance (Gain)"
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="bg-muted/30 rounded-lg p-4 text-sm mt-4">
                  <p className="font-medium mb-2">Interpretation:</p>
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-muted-foreground">
                    <li>• X-axis shows feature importance (Gain)</li>
                    <li>
                      • Gain = total improvement in model accuracy from splits
                      using this feature
                    </li>
                    <li>• Higher values indicate more influential features</li>
                    <li>
                      • Features are sorted by importance (highest at top)
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Monthly IC Heatmap */}
          {(ic_metrics as any)?.monthly_ic &&
            (ic_metrics as any).monthly_ic.length > 0 && (
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-blue-500" />
                    <CardTitle>Monthly IC Heatmap</CardTitle>
                    <InfoTooltip content="Shows IC values aggregated by month. Helps identify seasonal patterns or periods of strong/weak predictive power." />
                  </div>
                  <CardDescription>
                    Average IC by year and month
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <MonthlyICHeatmap data={(ic_metrics as any).monthly_ic} />
                  </div>
                </CardContent>
              </Card>
            )}

          {/* IC Distribution */}
          {(ic_metrics as any)?.ic_distribution && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* IC Histogram */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-indigo-500" />
                    <CardTitle>IC Distribution</CardTitle>
                    <InfoTooltip content="Histogram showing the distribution of daily IC values. A normal distribution centered above 0 indicates consistent predictive power." />
                  </div>
                  <CardDescription>
                    Distribution of daily IC values
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={(ic_metrics as any).ic_distribution.histogram}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="bin_center"
                          tick={{ fontSize: 10 }}
                          tickFormatter={(v) => v.toFixed(2)}
                        />
                        <YAxis tick={{ fontSize: 10 }} />
                        <RechartsTooltip
                          formatter={(value) => [value, "Count"]}
                          labelFormatter={(label) =>
                            `IC: ${(label as number).toFixed(3)}`
                          }
                        />
                        <Bar dataKey="count" fill="#6366f1" name="Frequency" />
                        <ReferenceLine
                          x={0}
                          stroke="#ef4444"
                          strokeDasharray="3 3"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                    <div className="bg-muted/50 rounded p-2">
                      <span className="text-muted-foreground">Skewness:</span>
                      <span className="ml-2 font-medium">
                        {(ic_metrics as any).ic_distribution.skewness?.toFixed(
                          3,
                        ) || "N/A"}
                      </span>
                    </div>
                    <div className="bg-muted/50 rounded p-2">
                      <span className="text-muted-foreground">Kurtosis:</span>
                      <span className="ml-2 font-medium">
                        {(ic_metrics as any).ic_distribution.kurtosis?.toFixed(
                          3,
                        ) || "N/A"}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Q-Q Plot */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-cyan-500" />
                    <CardTitle>Q-Q Plot</CardTitle>
                    <InfoTooltip content="Quantile-Quantile plot comparing IC distribution to normal distribution. Points close to the diagonal line indicate normality." />
                  </div>
                  <CardDescription>
                    IC distribution vs Normal distribution
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={(ic_metrics as any).ic_distribution.qq_plot}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="theoretical"
                          tick={{ fontSize: 10 }}
                          label={{
                            value: "Theoretical Quantiles",
                            position: "bottom",
                            fontSize: 11,
                          }}
                        />
                        <YAxis
                          dataKey="sample"
                          tick={{ fontSize: 10 }}
                          label={{
                            value: "Sample Quantiles",
                            angle: -90,
                            position: "insideLeft",
                            fontSize: 11,
                          }}
                        />
                        <RechartsTooltip
                          formatter={(value, name) => [
                            (value as number).toFixed(4),
                            name === "sample" ? "Sample" : "Theoretical",
                          ]}
                        />
                        <Line
                          type="monotone"
                          dataKey="sample"
                          stroke="#06b6d4"
                          dot={{ r: 2 }}
                          name="IC Quantiles"
                        />
                        <ReferenceLine
                          segment={[
                            {
                              x: -3,
                              y:
                                -3 *
                                  ((ic_metrics as any).ic_distribution.std ||
                                    0.05) +
                                ((ic_metrics as any).ic_distribution.mean || 0),
                            },
                            {
                              x: 3,
                              y:
                                3 *
                                  ((ic_metrics as any).ic_distribution.std ||
                                    0.05) +
                                ((ic_metrics as any).ic_distribution.mean || 0),
                            },
                          ]}
                          stroke="#ef4444"
                          strokeDasharray="3 3"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Cumulative Returns & Return Distribution */}
          {long_short_metrics && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Cumulative Returns */}
              {(long_short_metrics as any).cumulative_returns &&
                (long_short_metrics as any).cumulative_returns.length > 0 && (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-emerald-500" />
                        <CardTitle>Cumulative Returns</CardTitle>
                        <InfoTooltip content="Cumulative returns of the Long-Short strategy over time. Shows the total accumulated return from longing top stocks and shorting bottom stocks." />
                      </div>
                      <CardDescription>
                        Long-Short strategy cumulative performance
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={
                              (long_short_metrics as any).cumulative_returns
                            }
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              dataKey="datetime"
                              tick={{ fontSize: 10 }}
                              tickFormatter={(v) => v.substring(5, 10)}
                            />
                            <YAxis
                              tick={{ fontSize: 10 }}
                              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                            />
                            <RechartsTooltip
                              formatter={(value) => [
                                `${((value as number) * 100).toFixed(2)}%`,
                                "Cumulative Return",
                              ]}
                              labelFormatter={(label) =>
                                String(label).substring(0, 10)
                              }
                            />
                            <ReferenceLine
                              y={0}
                              stroke="#888"
                              strokeDasharray="3 3"
                            />
                            <Line
                              type="monotone"
                              dataKey="cumulative_return"
                              stroke="#10b981"
                              dot={false}
                              strokeWidth={2}
                              name="Cumulative Return"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                )}

              {/* Return Distribution */}
              {(long_short_metrics as any).return_distribution &&
                (long_short_metrics as any).return_distribution.length > 0 && (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-amber-500" />
                        <CardTitle>Return Distribution</CardTitle>
                        <InfoTooltip content="Distribution of daily Long-Short returns. A distribution shifted to the right indicates consistent positive returns." />
                      </div>
                      <CardDescription>
                        Daily Long-Short return distribution
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={
                              (long_short_metrics as any).return_distribution
                            }
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              dataKey="bin_center"
                              tick={{ fontSize: 10 }}
                              tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
                            />
                            <YAxis tick={{ fontSize: 10 }} />
                            <RechartsTooltip
                              formatter={(value) => [value, "Count"]}
                              labelFormatter={(label) =>
                                `Return: ${((label as number) * 100).toFixed(2)}%`
                              }
                            />
                            <Bar
                              dataKey="count"
                              fill="#f59e0b"
                              name="Frequency"
                            />
                            <ReferenceLine
                              x={0}
                              stroke="#ef4444"
                              strokeDasharray="3 3"
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                )}
            </div>
          )}

          {/* Turnover Analysis */}
          {(quality_metrics as any)?.turnover && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-5 w-5 text-rose-500" />
                  <CardTitle>Turnover Analysis</CardTitle>
                  <InfoTooltip content="Shows how much the top and bottom stock selections change daily. Lower turnover indicates more stable predictions and lower transaction costs." />
                </div>
                <CardDescription>
                  Top/Bottom stock selection stability (Avg Top:{" "}
                  {(
                    (quality_metrics as any).turnover.avg_top_turnover * 100
                  ).toFixed(1)}
                  %, Avg Bottom:{" "}
                  {(
                    (quality_metrics as any).turnover.avg_bottom_turnover * 100
                  ).toFixed(1)}
                  %)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={
                        (
                          quality_metrics as any
                        ).turnover.top_turnover_series?.map(
                          (item: any, idx: number) => ({
                            datetime: item.datetime,
                            top: item.turnover,
                            bottom:
                              (quality_metrics as any).turnover
                                .bottom_turnover_series?.[idx]?.turnover || 0,
                          }),
                        ) || []
                      }
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="datetime"
                        tick={{ fontSize: 10 }}
                        tickFormatter={(v) => v.substring(5, 10)}
                      />
                      <YAxis
                        tick={{ fontSize: 10 }}
                        tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                      />
                      <RechartsTooltip
                        formatter={(value, name) => [
                          `${((value as number) * 100).toFixed(1)}%`,
                          name === "top" ? "Top Turnover" : "Bottom Turnover",
                        ]}
                        labelFormatter={(label) =>
                          String(label).substring(0, 10)
                        }
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="top"
                        stroke="#22c55e"
                        dot={false}
                        strokeWidth={1.5}
                        name="Top Turnover"
                      />
                      <Line
                        type="monotone"
                        dataKey="bottom"
                        stroke="#ef4444"
                        dot={false}
                        strokeWidth={1.5}
                        name="Bottom Turnover"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="bg-muted/30 rounded-lg p-4 text-sm mt-4">
                  <p className="font-medium mb-2">Interpretation:</p>
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-muted-foreground">
                    <li>• Lower turnover = more stable predictions</li>
                    <li>• High turnover increases transaction costs</li>
                    <li>• Typical good turnover: 10-30% daily</li>
                    <li>• Very high turnover (&gt;50%) may indicate noise</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// Monthly IC Heatmap Component
function MonthlyICHeatmap({
  data,
}: {
  data: Array<{ year: number; month: number; ic: number }>;
}) {
  // Group data by year
  const years = [...new Set(data.map((d) => d.year))].sort();
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  // Create a map for quick lookup
  const icMap = new Map<string, number>();
  data.forEach((d) => {
    icMap.set(`${d.year}-${d.month}`, d.ic);
  });

  // Get color based on IC value
  const getColor = (ic: number | undefined) => {
    if (ic === undefined) return "bg-gray-100 dark:bg-gray-800";
    if (ic >= 0.05) return "bg-green-500 text-white";
    if (ic >= 0.03) return "bg-green-400 text-white";
    if (ic >= 0.01) return "bg-green-200 dark:bg-green-800";
    if (ic >= 0) return "bg-gray-200 dark:bg-gray-700";
    if (ic >= -0.01) return "bg-red-200 dark:bg-red-800";
    if (ic >= -0.03) return "bg-red-400 text-white";
    return "bg-red-500 text-white";
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="p-2 text-left font-medium">Year</th>
            {months.map((m) => (
              <th key={m} className="p-2 text-center font-medium w-12">
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((year) => (
            <tr key={year}>
              <td className="p-2 font-medium">{year}</td>
              {months.map((_, monthIdx) => {
                const ic = icMap.get(`${year}-${monthIdx + 1}`);
                return (
                  <td key={monthIdx} className="p-1">
                    <div
                      className={`w-full h-8 rounded flex items-center justify-center text-xs font-medium ${getColor(ic)}`}
                      title={
                        ic !== undefined ? `IC: ${ic.toFixed(4)}` : "No data"
                      }
                    >
                      {ic !== undefined ? ic.toFixed(2) : "-"}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-center gap-4 mt-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span>&lt;-0.03</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-red-200 dark:bg-red-800 rounded"></div>
          <span>-0.03~0</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <span>0~0.01</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-200 dark:bg-green-800 rounded"></div>
          <span>0.01~0.03</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <span>&gt;0.05</span>
        </div>
      </div>
    </div>
  );
}
