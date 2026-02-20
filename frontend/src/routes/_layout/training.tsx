import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  FileText,
  Settings,
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
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import { TrainingService } from "@/client";
import { toast } from "sonner";

export const Route = createFileRoute("/_layout/training")({
  component: TrainingWorkflow,
  head: () => ({ meta: [{ title: "Training Workflow - Qlib Quantbot" }] }),
});

// Helper function to format file size
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

// Helper function to format date
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleString();
  } catch {
    return dateStr;
  }
}

function TrainingWorkflow() {
  const queryClient = useQueryClient();

  // Query for training configuration
  const { data: configData, isLoading: configLoading } = useQuery({
    queryKey: ["trainingConfig"],
    queryFn: () => TrainingService.getTrainingConfig(),
  });

  // Query for trained models
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ["trainedModels"],
    queryFn: () => TrainingService.listModels(),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Mutation for starting training
  const startTrainingMutation = useMutation({
    mutationFn: () => TrainingService.startTraining(),
    onSuccess: (response) => {
      if (response.status === "success") {
        toast.success(
          `Training completed! ${response.test_predictions_count} predictions generated.`,
        );
      } else {
        toast.error(`Training failed: ${response.error || response.message}`);
      }
      // Refresh models list after training
      queryClient.invalidateQueries({ queryKey: ["trainedModels"] });
    },
    onError: (error) => {
      toast.error(`Training failed: ${error.message}`);
    },
  });

  // Extract model config from response
  const config = configData?.config;
  const modelConfig = config?.task?.model;
  const modelKwargs = modelConfig?.kwargs || {};

  // Extract models list
  const models = modelsData?.models || [];

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div>
            <h1 className="text-2xl font-bold">Training Workflow</h1>
            <p className="text-muted-foreground">
              Train machine learning models using Qlib
            </p>
          </div>

          {/* Model Configuration Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-blue-500" />
                <CardTitle className="text-lg">Model Configuration</CardTitle>
              </div>
              <CardDescription>
                Configuration from training_config.yaml
              </CardDescription>
            </CardHeader>
            <CardContent>
              {configLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Loading configuration...
                </div>
              ) : configData?.status === "error" ? (
                <div className="flex items-center gap-2 text-red-500">
                  <XCircle className="h-4 w-4" />
                  {configData.error || "Failed to load configuration"}
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Model Type */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-muted-foreground">
                        Model Type
                      </Label>
                      <div className="flex items-center gap-2 mt-1">
                        <Cpu className="h-4 w-4 text-green-500" />
                        <span className="font-medium">
                          {modelConfig?.class || "N/A"}
                        </span>
                      </div>
                    </div>
                    <div>
                      <Label className="text-muted-foreground">
                        Module Path
                      </Label>
                      <div className="text-sm font-mono mt-1">
                        {modelConfig?.module_path || "N/A"}
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Hyperparameters */}
                  <div>
                    <Label className="text-muted-foreground mb-2 block">
                      Hyperparameters
                    </Label>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {Object.entries(modelKwargs).map(([key, value]) => (
                        <div
                          key={key}
                          className="bg-muted/50 rounded-md p-2 text-sm"
                        >
                          <span className="text-muted-foreground">{key}:</span>{" "}
                          <span className="font-medium">
                            {typeof value === "number"
                              ? value.toLocaleString()
                              : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Trained Models Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-purple-500" />
                <CardTitle className="text-lg">Trained Models</CardTitle>
              </div>
              <CardDescription>
                {models.length > 0
                  ? `${models.length} model(s) available`
                  : "No models trained yet"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {modelsLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Loading models...
                </div>
              ) : models.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p>No models have been trained yet.</p>
                  <p className="text-sm">
                    Click "Start Training" to train your first model.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {models.map((model: any, index: number) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-md"
                    >
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                        <div>
                          <div className="font-medium">{model.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {formatFileSize(model.size_bytes)}
                          </div>
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <Clock className="h-4 w-4 inline mr-1" />
                        {formatDate(model.modified_at)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Training Status Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <RefreshCw
                  className={`h-5 w-5 ${startTrainingMutation.isPending ? "animate-spin text-blue-500" : "text-gray-500"}`}
                />
                <CardTitle className="text-lg">Training Status</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {startTrainingMutation.isPending ? (
                    <>
                      <Badge variant="default" className="bg-blue-500">
                        Training
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        Training in progress... This may take several minutes.
                      </span>
                    </>
                  ) : startTrainingMutation.isSuccess ? (
                    <>
                      <Badge
                        variant="default"
                        className={
                          startTrainingMutation.data?.status === "success"
                            ? "bg-green-500"
                            : "bg-red-500"
                        }
                      >
                        {startTrainingMutation.data?.status === "success"
                          ? "Completed"
                          : "Failed"}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {startTrainingMutation.data?.message}
                        {startTrainingMutation.data?.test_predictions_count >
                          0 &&
                          ` (${startTrainingMutation.data.test_predictions_count} predictions)`}
                      </span>
                    </>
                  ) : startTrainingMutation.isError ? (
                    <>
                      <Badge variant="destructive">Error</Badge>
                      <span className="text-sm text-red-500">
                        {startTrainingMutation.error?.message}
                      </span>
                    </>
                  ) : (
                    <>
                      <Badge variant="secondary">Idle</Badge>
                      <span className="text-sm text-muted-foreground">
                        Ready to start training
                      </span>
                    </>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Start Training Button */}
          <div className="flex justify-center">
            <Button
              size="lg"
              onClick={() => startTrainingMutation.mutate()}
              disabled={startTrainingMutation.isPending}
              className="px-8"
            >
              {startTrainingMutation.isPending ? (
                <>
                  <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
                  Training...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-5 w-5" />
                  Start Training
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
