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
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  Database,
  RefreshCw,
  Trash2,
  TrendingUp,
  Clock,
  BarChart3,
  HardDrive,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { DataSourceService } from "@/client";

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

  // Dialog state for details
  const [missingDataDialogOpen, setMissingDataDialogOpen] = useState(false);
  const [anomaliesDialogOpen, setAnomaliesDialogOpen] = useState(false);

  // Query for data source status
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["dataSourceStatus"],
    queryFn: () => DataSourceService.getDataSourceStatusEndpoint(),
    refetchInterval: 5000,
  });

  // Query for data health metrics
  const { data: healthMetrics } = useQuery({
    queryKey: ["dataHealthMetrics"],
    queryFn: () => DataSourceService.getDataHealthEndpoint(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Mutation for clearing data
  const clearDataMutation = useMutation({
    mutationFn: () => DataSourceService.clearDataSourceEndpoint(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataSourceStatus"] });
    },
  });

  // Mutation for exporting data
  const exportDataMutation = useMutation({
    mutationFn: async () => {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const response = await fetch(`${apiUrl}/api/v1/data-source/export-data`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Export failed");
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get("Content-Disposition");
      const filename = contentDisposition
        ? contentDisposition.split("filename=")[1].replace(/"/g, "")
        : `qlib_data_export_${new Date().toISOString().slice(0, 10)}.csv`;

      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
  });

  // Helper function to get frequency display text
  const getFrequencyText = () => {
    if (!status?.features || status.features.length === 0) return "Unknown";
    const firstFeature = status.features[0];
    if (firstFeature.includes(".1min")) return "Minute (1m)";
    if (firstFeature.includes(".day")) return "Daily (1d)";
    return "Unknown";
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
              Monitor your quantitative data quality and status
            </p>
          </div>

          {/* Summary Cards */}
          {status && status.source_name && status.source_name !== "unknown" && (
            <div className="grid gap-4 md:grid-cols-5">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Data Source
                  </CardTitle>
                  <Database className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{status.source_name}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Stock Pool
                  </CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{status.stock_pool}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Frequency
                  </CardTitle>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{getFrequencyText()}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Instruments
                  </CardTitle>
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {status.instruments_count}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Data Size
                  </CardTitle>
                  <HardDrive className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {status.data_size_mb} MB
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

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
                    <div className="col-span-4">
                      <Label className="text-sm font-medium">Features</Label>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {status.features
                          ?.filter(
                            (f) => !status.label || !f.startsWith(status.label),
                          )
                          .map((feature) => (
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
                      <div className="mt-3">
                        <Label className="text-sm font-medium">
                          Label (Prediction Target)
                        </Label>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {status.label ? (
                            <Badge
                              variant="default"
                              className="text-xs bg-amber-500 hover:bg-amber-600"
                            >
                              {status.label}
                            </Badge>
                          ) : (
                            <span className="text-sm text-muted-foreground">
                              No label configured
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  <Separator className="my-4" />
                  <div className="flex justify-center gap-3">
                    <Button
                      onClick={() => exportDataMutation.mutate()}
                      variant="default"
                      size="sm"
                      disabled={!status || exportDataMutation.isPending}
                      className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-300 disabled:text-gray-500"
                    >
                      <RefreshCw
                        className={`h-4 w-4 ${exportDataMutation.isPending ? "animate-spin" : ""}`}
                      />
                      {exportDataMutation.isPending
                        ? "Exporting..."
                        : "Export Data"}
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

          {/* Data Quality Metrics Card */}
          {healthMetrics && healthMetrics.data_exists && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  Data Quality Metrics
                </CardTitle>
                <CardDescription>
                  Comprehensive data health analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Completeness</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-lg font-semibold">
                        {healthMetrics.completeness_percentage.toFixed(1)}%
                      </p>
                      {healthMetrics.completeness_percentage >= 95 ? (
                        <Badge variant="default" className="bg-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Good
                        </Badge>
                      ) : healthMetrics.completeness_percentage >= 80 ? (
                        <Badge variant="default" className="bg-yellow-600">
                          <AlertTriangle className="h-3 w-3 mr-1" />
                          Warning
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <XCircle className="h-3 w-3 mr-1" />
                          Poor
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium">Missing Data</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-lg font-semibold">
                        {healthMetrics.missing_data_count} instruments
                      </p>
                      {healthMetrics.missing_data_count > 0 && (
                        <Button
                          variant="link"
                          size="sm"
                          className="h-auto p-0 text-blue-600"
                          onClick={() => setMissingDataDialogOpen(true)}
                        >
                          Details
                        </Button>
                      )}
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium">Anomalies</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-lg font-semibold">
                        {healthMetrics.anomaly_count} detected
                      </p>
                      {healthMetrics.anomaly_count > 0 && (
                        <Button
                          variant="link"
                          size="sm"
                          className="h-auto p-0 text-blue-600"
                          onClick={() => setAnomaliesDialogOpen(true)}
                        >
                          Details
                        </Button>
                      )}
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium">Integrity</Label>
                    <div className="flex flex-col gap-1 mt-1">
                      {healthMetrics.integrity_checks.required_columns && (
                        <Badge variant="outline" className="w-fit">
                          <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                          Columns OK
                        </Badge>
                      )}
                      {healthMetrics.integrity_checks.factor_column && (
                        <Badge variant="outline" className="w-fit">
                          <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                          Factor OK
                        </Badge>
                      )}
                      {healthMetrics.integrity_checks.directory_case && (
                        <Badge variant="outline" className="w-fit">
                          <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                          Naming OK
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Status Messages */}
          {clearDataMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {clearDataMutation.error?.message}
              </AlertDescription>
            </Alert>
          )}

          {clearDataMutation.isSuccess && (
            <Alert>
              <AlertDescription>Data cleared successfully!</AlertDescription>
            </Alert>
          )}
        </div>
      </div>

      {/* Missing Data Details Dialog */}
      <Dialog
        open={missingDataDialogOpen}
        onOpenChange={setMissingDataDialogOpen}
      >
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Missing Data Details</DialogTitle>
            <DialogDescription>
              Instruments with missing OHLCV data
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {healthMetrics?.missing_data_details?.map((detail, index) => (
              <div key={index} className="border-b pb-3">
                <p className="font-semibold text-sm mb-2">
                  {detail.instrument}
                </p>
                <div className="grid grid-cols-5 gap-2 text-xs">
                  {detail.open > 0 && (
                    <div>
                      <span className="text-muted-foreground">Open:</span>{" "}
                      <span className="font-medium">{detail.open}</span>
                    </div>
                  )}
                  {detail.high > 0 && (
                    <div>
                      <span className="text-muted-foreground">High:</span>{" "}
                      <span className="font-medium">{detail.high}</span>
                    </div>
                  )}
                  {detail.low > 0 && (
                    <div>
                      <span className="text-muted-foreground">Low:</span>{" "}
                      <span className="font-medium">{detail.low}</span>
                    </div>
                  )}
                  {detail.close > 0 && (
                    <div>
                      <span className="text-muted-foreground">Close:</span>{" "}
                      <span className="font-medium">{detail.close}</span>
                    </div>
                  )}
                  {detail.volume > 0 && (
                    <div>
                      <span className="text-muted-foreground">Volume:</span>{" "}
                      <span className="font-medium">{detail.volume}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {(!healthMetrics?.missing_data_details ||
              healthMetrics.missing_data_details.length === 0) && (
              <p className="text-sm text-muted-foreground">
                No missing data found.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Anomalies Details Dialog */}
      <Dialog open={anomaliesDialogOpen} onOpenChange={setAnomaliesDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Data Anomalies Details</DialogTitle>
            <DialogDescription>
              Large step changes detected in OHLCV data
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {healthMetrics?.anomalies?.map((anomaly, index) => (
              <div key={index} className="border-b pb-3">
                <div className="grid grid-cols-4 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Instrument:</span>{" "}
                    <span className="font-medium">{anomaly.instrument}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Column:</span>{" "}
                    <span className="font-medium">{anomaly.column}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Date:</span>{" "}
                    <span className="font-medium">{anomaly.date}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Change:</span>{" "}
                    <Badge variant="destructive">
                      {(anomaly.pct_change * 100).toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
            {(!healthMetrics?.anomalies ||
              healthMetrics.anomalies.length === 0) && (
              <p className="text-sm text-muted-foreground">
                No anomalies detected.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
