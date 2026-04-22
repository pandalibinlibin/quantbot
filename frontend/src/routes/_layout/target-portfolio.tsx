import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

function TargetPortfolioPage() {
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

  // Show loading state
  if (portfolioLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading portfolio...</span>
      </div>
    );
  }

  // Show error state
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
        <p className="text-muted-foreground">View target portfolio data</p>
      </div>

      {/* Portfolio Data */}
      {latestPortfolio?.success ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              Portfolio Summary
            </CardTitle>
            <CardDescription>
              Generated: {latestPortfolio.generated_at || "N/A"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-3">
                <div className="text-sm text-muted-foreground">Trade Date</div>
                <div className="text-lg font-semibold">
                  {latestPortfolio.trade_date || "-"}
                </div>
              </div>
              <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-3">
                <div className="text-sm text-muted-foreground">Total Value</div>
                <div className="text-lg font-semibold">
                  ¥{(latestPortfolio.total_value || 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-3">
                <div className="text-sm text-muted-foreground">Positions</div>
                <div className="text-lg font-semibold">
                  {latestPortfolio.positions?.length || 0}
                </div>
              </div>
              <div className="bg-orange-50 dark:bg-orange-950/30 rounded-lg p-3">
                <div className="text-sm text-muted-foreground">Signal Date</div>
                <div className="text-lg font-semibold">
                  {latestPortfolio.signal_for_date || "-"}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
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
