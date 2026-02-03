import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AlertCircle, Database, RefreshCw, Trash2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { DataSourceService } from "@/client";
import type { DownloadDataRequest } from "@/client";

export const Route = createFileRoute("/_layout/data-sources")({
  component: DataSourcesPage,
  head: () => ({
    meta: [
      {
        title: "Data Sources - QuantBot",
      },
    ],
  }),
});

function DataSourcesPage() {
  const queryClient = useQueryClient();

  // Form state
  const [source, setSource] = useState<string>("yahoo");
  const [stockPool, setStockPool] = useState<string>("csi300");
  const [startDate, setStartDate] = useState<string>("2024-01-01");
  const [endDate, setEndDate] = useState<string>("2024-01-31");

  // Query for data source status
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["dataSourceStatus"],
    queryFn: () => DataSourceService.getDataSourceStatusEndpoint(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Mutation for clearing data
  const clearDataMutation = useMutation({
    mutationFn: () => DataSourceService.clearDataSourceEndpoint(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataSourceStatus"] });
    },
  });

  // Mutation for downloading data (reset mode)
  const downloadDataMutation = useMutation({
    mutationFn: (request: DownloadDataRequest) =>
      DataSourceService.downloadDataSourceEndpoint({ requestBody: request }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataSourceStatus"] });
    },
  });

  // Handler functions
  const handleDownload = () => {
    const request: DownloadDataRequest = {
      source,
      stock_pool: stockPool,
      start_date: startDate,
      end_date: endDate,
    };
    downloadDataMutation.mutate(request);
  };

  const handleIncremental = () => {
    // For incremental update, use current data source and stock pool from status
    // but automatically update to latest date (today)
    const today = new Date().toISOString().split("T")[0];

    const request: DownloadDataRequest = {
      source: status?.source_name || source,
      stock_pool: status?.stock_pool || stockPool,
      start_date: status?.data_range_end || startDate, // Start from last available date
      end_date: today, // Update to today
      incremental: true,
    };
    downloadDataMutation.mutate(request);
  };

  const handleClear = () => {
    clearDataMutation.mutate();
  };

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Data Sources</h1>
            <p className="text-muted-foreground">
              Manage your quantitative data sources and collections
            </p>
          </div>

          {/* Current Status Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Current Data Status
              </CardTitle>
              <CardDescription>
                Overview of your current data collection
              </CardDescription>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Loading status...
                </div>
              ) : status &&
                status.source_name &&
                status.source_name !== "unknown" ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <Label className="text-sm font-medium">Data Source</Label>
                      <p className="text-lg font-semibold">
                        {status.source_name}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Stock Pool</Label>
                      <p className="text-lg font-semibold">
                        {status.stock_pool}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Instruments</Label>
                      <p className="text-lg font-semibold">
                        {status.instruments_count}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Data Size</Label>
                      <p className="text-lg font-semibold">
                        {status.data_size_mb} MB
                      </p>
                    </div>
                    <div className="col-span-2">
                      <Label className="text-sm font-medium">Date Range</Label>
                      <p className="text-lg font-semibold">
                        {status.data_range_start} to {status.data_range_end}
                      </p>
                    </div>
                    <div className="col-span-2">
                      <Label className="text-sm font-medium">Features</Label>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {status.features?.map((feature) => (
                          <Badge
                            key={feature}
                            variant="secondary"
                            className="text-xs"
                          >
                            {feature}
                          </Badge>
                        )) || (
                          <span className="text-sm text-muted-foreground">
                            No features available
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Separator className="my-4" />
                  <div className="flex justify-center gap-3">
                    <Button
                      onClick={handleIncremental}
                      variant="default"
                      size="sm"
                      disabled={!status || downloadDataMutation.isPending}
                      className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 disabled:text-gray-500"
                    >
                      <RefreshCw
                        className={`h-4 w-4 ${downloadDataMutation.isPending ? "animate-spin" : ""}`}
                      />
                      {downloadDataMutation.isPending
                        ? "Updating..."
                        : "Incremental Update"}
                    </Button>
                    <Button
                      onClick={handleClear}
                      variant="destructive"
                      size="sm"
                      disabled={!status || clearDataMutation.isPending}
                      className="flex items-center gap-2 disabled:bg-gray-300 disabled:text-gray-500"
                    >
                      <Trash2 className="h-4 w-4" />
                      {clearDataMutation.isPending
                        ? "Clearing..."
                        : "Clear Data"}
                    </Button>
                  </div>
                </>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No data available. Please download data first.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Data Collection Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Data Collection Configuration</CardTitle>
              <CardDescription>
                Configure your data collection parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="source">Data Source</Label>
                  <Select value={source} onValueChange={setSource}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yahoo">Yahoo Finance</SelectItem>
                      <SelectItem value="tushare" disabled>
                        Tushare (Coming Soon)
                      </SelectItem>
                      <SelectItem value="akshare" disabled>
                        AKShare (Coming Soon)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="stockPool">Stock Pool</Label>
                  <Select value={stockPool} onValueChange={setStockPool}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="csi300">CSI 300</SelectItem>
                      <SelectItem value="csi500">CSI 500</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="startDate">Start Date</Label>
                  <Input
                    id="startDate"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="endDate">End Date</Label>
                  <Input
                    id="endDate"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <Separator className="my-4" />
              <Button
                onClick={handleDownload}
                disabled={downloadDataMutation.isPending}
                className="flex items-center gap-2 w-full"
              >
                <RefreshCw
                  className={`h-4 w-4 ${downloadDataMutation.isPending ? "animate-spin" : ""}`}
                />
                {downloadDataMutation.isPending
                  ? "Downloading..."
                  : "Download Data"}
              </Button>
            </CardContent>
          </Card>

          {/* Status Messages */}
          {(downloadDataMutation.isError || clearDataMutation.isError) && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {downloadDataMutation.error?.message ||
                  clearDataMutation.error?.message}
              </AlertDescription>
            </Alert>
          )}

          {(downloadDataMutation.isSuccess || clearDataMutation.isSuccess) && (
            <Alert>
              <AlertDescription>
                Operation completed successfully!
              </AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
}
