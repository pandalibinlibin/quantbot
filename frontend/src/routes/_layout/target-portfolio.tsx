import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Loader2, Info } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OpenAPI } from "@/client";

// API helper functions
const apiHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

async function fetchLatestPortfolio() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/dashboard/latest-portfolio`,
    { headers: apiHeaders() },
  );
  if (!response.ok) throw new Error("Failed to fetch latest portfolio");
  return response.json();
}

export const Route = createFileRoute("/_layout/target-portfolio")({
  component: TargetPortfolioPage,
  head: () => ({
    meta: [{ title: "Target Portfolio - QuantBot" }],
  }),
});

function ConfidenceLabel({
  label,
  percentile,
}: {
  label: string;
  percentile: number | null;
}) {
  const colorMap: Record<string, string> = {
    极强: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400",
    较强: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
    正常: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
    较弱: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
    极弱: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
  };
  const color =
    colorMap[label] ||
    "bg-gray-100 text-gray-700 dark:bg-gray-950 dark:text-gray-400";
  const percentileText =
    percentile != null ? ` Top ${(100 - percentile).toFixed(0)}%` : "";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}
    >
      {label}
      {percentileText}
    </span>
  );
}

function TargetPortfolioPage() {
  const {
    data: latestPortfolio,
    isLoading: portfolioLoading,
    error: portfolioError,
  } = useQuery({
    queryKey: ["latestPortfolio"],
    queryFn: fetchLatestPortfolio,
    refetchOnWindowFocus: true,
    staleTime: 30000,
  });

  if (portfolioLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading portfolio...</span>
      </div>
    );
  }

  if (portfolioError) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-red-500">
          Failed to load portfolio: {portfolioError.message}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold">Target Portfolio</h1>
        <p className="text-muted-foreground">
          Latest target holdings based on model signals
        </p>
      </div>

      {latestPortfolio?.success ? (
        <>
          {/* Signal Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-600" />
                Signal Overview
              </CardTitle>
              <CardDescription>
                Generated: {latestPortfolio.generated_at || "N/A"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
                  <div className="text-sm text-muted-foreground">
                    Signal Date
                  </div>
                  <div className="text-lg font-semibold">
                    {latestPortfolio.signal_for_date || "-"}
                  </div>
                </div>
                <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-3">
                  <div className="text-sm text-muted-foreground">
                    Trade Date
                  </div>
                  <div className="text-lg font-semibold">
                    {latestPortfolio.trade_date || "-"}
                  </div>
                </div>
                <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-3">
                  <div className="text-sm text-muted-foreground">Positions</div>
                  <div className="text-lg font-semibold">
                    {latestPortfolio.positions?.length || 0}
                  </div>
                </div>
                <div className="bg-orange-50 dark:bg-orange-950/30 rounded-lg p-3">
                  <div className="text-sm text-muted-foreground">
                    Confidence
                  </div>
                  <div className="mt-1">
                    {latestPortfolio.confidence_label ? (
                      <ConfidenceLabel
                        label={latestPortfolio.confidence_label}
                        percentile={latestPortfolio.confidence_percentile}
                      />
                    ) : (
                      <span className="text-lg font-semibold">-</span>
                    )}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-950/30 rounded-lg p-3">
                  <div className="text-sm text-muted-foreground">
                    Weight Mode
                  </div>
                  <div className="text-lg font-semibold capitalize">
                    {latestPortfolio.weight_method?.replace("_", " ") || "-"}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Signal Interpretation */}
          {latestPortfolio.confidence_interpretation && (
            <Card>
              <CardContent className="py-4">
                <div className="flex items-start gap-3">
                  <div className="shrink-0 mt-0.5 text-2xl">💡</div>
                  <div>
                    <div className="font-medium text-sm text-muted-foreground mb-1">
                      Signal Interpretation
                    </div>
                    <p className="text-base">
                      {latestPortfolio.confidence_interpretation}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Target Holdings Table */}
          <Card>
            <CardHeader>
              <CardTitle>Target Holdings</CardTitle>
              <CardDescription>
                Top {latestPortfolio.topk || latestPortfolio.positions?.length}{" "}
                holdings ranked by model prediction score
              </CardDescription>
            </CardHeader>
            <CardContent>
              {latestPortfolio.positions?.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16 text-center">Rank</TableHead>
                      <TableHead className="w-28">Symbol</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead className="w-24 text-right">Score</TableHead>
                      <TableHead className="w-24 text-right">Weight</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {latestPortfolio.positions.map(
                      (pos: Record<string, unknown>, idx: number) => (
                        <TableRow key={String(pos.symbol) || idx}>
                          <TableCell className="text-center font-medium">
                            {Number(pos.rank) || idx + 1}
                          </TableCell>
                          <TableCell className="font-mono font-semibold">
                            {String(pos.symbol)}
                          </TableCell>
                          <TableCell>{String(pos.name || "-")}</TableCell>
                          <TableCell className="text-right font-mono">
                            {pos.score != null
                              ? Number(pos.score).toFixed(4)
                              : "-"}
                          </TableCell>
                          <TableCell className="text-right font-semibold">
                            {pos.weight != null
                              ? `${(Number(pos.weight) * 100).toFixed(1)}%`
                              : "-"}
                          </TableCell>
                        </TableRow>
                      ),
                    )}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No positions
                </p>
              )}
            </CardContent>
          </Card>

          {/* Footer Notes */}
          <Card className="border-dashed">
            <CardContent className="py-4">
              <div className="flex items-start gap-2 text-sm text-muted-foreground">
                <Info className="h-4 w-4 mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <p>
                    Weight 为模型推荐的配置比例，请按自身资金规模等比例缩放。
                  </p>
                  <p>
                    Score 越高代表模型预期收益越高。Confidence
                    百分位基于历史信号强度分布，反映模型对本次推荐的区分能力。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-muted-foreground">
              <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">No Portfolio Data</p>
              <p className="text-sm mt-1">
                Click Update Portfolio to generate target portfolio
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
