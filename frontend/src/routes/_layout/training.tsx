import { createFileRoute } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { QlibWorkflowsService } from "@/client";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const Route = createFileRoute("/_layout/training")({
  component: TrainingWorkflow,
  head: () => ({ meta: [{ title: "Training Workflow - Qlib Quantbot" }] }),
});

const trainingFormSchema = z.object({
  experiment_name: z.string().min(1).max(100),
  model_type: z.string().min(1),
  factor_engine: z.string().min(1),
  instruments: z.string().min(1),
  freq: z.string().min(1),
  data_start_date: z.string().min(1),
  data_end_date: z.string().min(1),
  fit_start_date: z.string().min(1),
  fit_end_date: z.string().min(1),
  train_start_date: z.string().min(1),
  train_end_date: z.string().min(1),
  valid_start_date: z.string().min(1),
  valid_end_date: z.string().min(1),
  test_start_date: z.string().min(1),
  test_end_date: z.string().min(1),
});

type TrainingFormData = z.infer<typeof trainingFormSchema>;

function TrainingWorkflow() {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingStage, setTrainingStage] = useState<string>("");

  const form = useForm<TrainingFormData>({
    resolver: zodResolver(trainingFormSchema),
    defaultValues: {
      experiment_name:
        "qlib-training-" + new Date().toISOString().split("T")[0],
      model_type: "LGBModel",
      factor_engine: "Alpha158",
      instruments: "csi300",
      freq: "day",
      data_start_date: "2019-01-01",
      data_end_date: "2020-09-25",
      fit_start_date: "2019-01-01",
      fit_end_date: "2019-12-31",
      train_start_date: "2019-01-01",
      train_end_date: "2019-12-31",
      valid_start_date: "2020-01-01",
      valid_end_date: "2020-06-30",
      test_start_date: "2020-07-01",
      test_end_date: "2020-09-25",
    },
  });

  const onSubmit = async (data: TrainingFormData) => {
    setIsTraining(true);
    setTrainingStage("Preparing request...");

    try {
      const requestBody = {
        experiment_name: data.experiment_name,
        task: {
          model: {
            class_name: data.model_type,
            kwargs: {}, // Backend will fill with default hyperparameters
          },
          dataset: {
            class_name: "DatasetH",
            module_path: null, // Backend will fill automatically
            kwargs: {
              handler: {
                class_name: data.factor_engine,
                module_path: null, // Backend will fill automatically
                kwargs: {
                  start_time: data.data_start_date,
                  end_time: data.data_end_date,
                  fit_start_time: data.fit_start_date,
                  fit_end_time: data.fit_end_date,
                  instruments: data.instruments,
                  freq: data.freq,
                },
              },
              segments: {
                train: [data.train_start_date, data.train_end_date],
                valid: [data.valid_start_date, data.valid_end_date],
                test: [data.test_start_date, data.test_end_date],
              },
            },
          },
        },
      };

      console.log("Sending training request:", requestBody);

      setTrainingStage("Initializing Qlib and preparing dataset...");
      const response = await QlibWorkflowsService.executeTrainingWorkflow({
        requestBody,
      });

      console.log("Training workflow response:", response);
      setTrainingStage("Training completed!");

      setTimeout(() => {
        alert(
          `Training completed! Predictions count: ${response.predictions_count}`,
        );
        setIsTraining(false);
        setTrainingStage("");
      }, 500);
    } catch (error) {
      console.error("Training workflow failed:", error);
      setTrainingStage("Training failed");

      setTimeout(() => {
        alert("Training failed. Please check the console for details.");
        setIsTraining(false);
        setTrainingStage("");
      }, 500);
    }
  };

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <Card className="h-full m-0 rounded-none border-0 flex flex-col">
        <CardHeader className="py-1.5 px-3 border-b bg-gray-50 flex-shrink-0">
          <CardTitle className="text-sm">Training Workflow</CardTitle>
          <CardDescription className="text-[10px]">
            Configure model training parameters
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 p-0 overflow-hidden">
          <div className="h-full overflow-y-auto">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="p-3 space-y-2"
              >
                <div className="border rounded p-2">
                  <h3 className="font-semibold text-xs mb-1.5">
                    Basic Configuration
                  </h3>
                  <FormField
                    control={form.control}
                    name="experiment_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">
                          Experiment Name
                        </FormLabel>
                        <FormControl>
                          <Input {...field} className="h-7 text-xs" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="border rounded p-2 space-y-1.5">
                  <h3 className="font-semibold text-xs mb-1.5">
                    Model & Features
                  </h3>
                  <FormField
                    control={form.control}
                    name="factor_engine"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">Factor Engine</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="Alpha158">
                              Alpha158 (158 factors)
                            </SelectItem>
                            <SelectItem value="Alpha101">
                              Alpha101 (101 factors)
                            </SelectItem>
                            <SelectItem value="Alpha360">
                              Alpha360 (360 factors)
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="model_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">Model Type</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="LGBModel">LightGBM</SelectItem>
                            <SelectItem value="XGBModel">XGBoost</SelectItem>
                            <SelectItem value="LinearModel">Linear</SelectItem>
                            <SelectItem value="MLPModel">
                              MLP Neural Network
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="instruments"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">Instruments</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="csi300">CSI 300</SelectItem>
                            <SelectItem value="csi500">CSI 500</SelectItem>
                            <SelectItem value="csi800">CSI 800</SelectItem>
                            <SelectItem value="all">All Stocks</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="freq"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-xs">Frequency</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="day">Daily</SelectItem>
                            <SelectItem value="week">Weekly</SelectItem>
                            <SelectItem value="month">Monthly</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="border rounded p-2 space-y-1.5">
                  <h3 className="font-semibold text-xs mb-1.5">
                    Time Configuration
                  </h3>

                  <div>
                    <label className="text-xs font-medium block mb-1">
                      Data Collection Period
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <FormField
                        control={form.control}
                        name="data_start_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">Start</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="data_end_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">End</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium block mb-1">
                      Model Fitting Period
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <FormField
                        control={form.control}
                        name="fit_start_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">Start</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="fit_end_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">End</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium block mb-1">
                      Training Period
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <FormField
                        control={form.control}
                        name="train_start_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">Start</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="train_end_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">End</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium block mb-1">
                      Validation Period
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <FormField
                        control={form.control}
                        name="valid_start_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">Start</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="valid_end_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">End</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium block mb-1">
                      Test Period
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <FormField
                        control={form.control}
                        name="test_start_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">Start</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="test_end_date"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-[10px]">End</FormLabel>
                            <FormControl>
                              <Input
                                type="date"
                                {...field}
                                className="h-7 text-[10px]"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>
                </div>

                {isTraining && trainingStage && (
                  <div className="flex items-center justify-center gap-2 py-2 px-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>{trainingStage}</span>
                  </div>
                )}

                <div className="flex justify-center pt-2 border-t">
                  <Button type="submit" className="px-8" disabled={isTraining}>
                    {isTraining ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Training...
                      </>
                    ) : (
                      "Start Training"
                    )}
                  </Button>
                </div>
              </form>
            </Form>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
