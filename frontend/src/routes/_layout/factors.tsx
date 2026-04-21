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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertCircle,
  Plus,
  Pencil,
  Trash2,
  FlaskConical,
  RefreshCw,
  Lock,
  Layers,
  Tag,
  Package,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Eye,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { FactorsService, DataSourceService } from "@/client";
import type { Factor, FactorCreate, FactorUpdate } from "@/client";

// Alpha158 factor info type
interface Alpha158Factor {
  name: string;
  expression: string;
  category: string;
}

interface Alpha158Info {
  name: string;
  display_name: string;
  enabled: boolean;
  description: string;
  factor_count: number;
  data_requirements: string[];
  factors: Alpha158Factor[];
}

export const Route = createFileRoute("/_layout/factors")({
  component: FactorsPage,
  head: () => ({
    meta: [
      {
        title: "Factors - QuantBot",
      },
    ],
  }),
});

function FactorsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string>("features");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingFactor, setEditingFactor] = useState<Factor | null>(null);
  const [showAlpha158Factors, setShowAlpha158Factors] = useState(false);

  // Form state for create/edit
  const [formName, setFormName] = useState("");
  const [formExpression, setFormExpression] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formType, setFormType] = useState<"feature" | "label">("feature");

  // Query for Alpha158 info
  const { data: alpha158Info } = useQuery<Alpha158Info>({
    queryKey: ["alpha158Info"],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const response = await fetch(
        `${apiUrl}/api/v1/factors/builtin-libraries/alpha158`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      );
      if (!response.ok) throw new Error("Failed to fetch Alpha158 info");
      return response.json();
    },
  });

  // Query for data source status (to get all available features)
  const { data: dataSourceStatus } = useQuery({
    queryKey: ["dataSourceStatus"],
    queryFn: () => DataSourceService.getDataSourceStatusEndpoint(),
  });

  // Query for user-created features from database
  const {
    data: customFeatures,
    isLoading: featuresLoading,
    error: featuresError,
  } = useQuery({
    queryKey: ["factors", "feature"],
    queryFn: () => FactorsService.getFactors({ factorType: "feature" }),
  });

  // Query for label config (from system_config.yaml, not user-editable)
  interface LabelConfig {
    region: string;
    expression: string;
    description: string;
    name: string;
    editable: boolean;
  }

  const {
    data: labelConfig,
    isLoading: labelsLoading,
    error: labelsError,
  } = useQuery<LabelConfig>({
    queryKey: ["labelConfig"],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const response = await fetch(`${apiUrl}/api/v1/factors/label-config`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (!response.ok) throw new Error("Failed to fetch label config");
      return response.json();
    },
  });

  // OHLCV + vwap base field names (without frequency suffix)
  const OHLCV_FIELDS = ["close", "open", "high", "low", "volume", "vwap"];

  // Get custom factor names (normalized to base name without .day/.1min suffix)
  const customFactorBaseNames = new Set(
    (customFeatures || []).map((f) =>
      f.name.replace(/\.(day|1min)$/, "").toLowerCase(),
    ),
  );

  // Filter data source features to only include true OHLCV fields (not custom factors)
  const builtinFeatures: Factor[] = (dataSourceStatus?.features || [])
    .filter((name) => {
      const baseName = name.replace(/\.(day|1min)$/, "").toLowerCase();
      // Only include if it's an OHLCV field AND not already a custom factor
      return (
        OHLCV_FIELDS.includes(baseName) && !customFactorBaseNames.has(baseName)
      );
    })
    .map((name) => ({
      id: `builtin-${name}`,
      name: name,
      expression: `$${name.replace(/\.(day|1min)$/, "")}`,
      description: OHLCV_FIELDS.slice(0, 5).includes(
        name.replace(/\.(day|1min)$/, "").toLowerCase(),
      )
        ? "Built-in OHLCV field"
        : "Built-in data field",
      factor_type: "feature" as const,
      status: "active" as const,
      created_by: "system",
      _isBuiltin: true,
    }));

  // Combined features list: builtin first, then custom
  const features = [...builtinFeatures, ...(customFeatures || [])];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: FactorCreate) =>
      FactorsService.createFactor({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["factors"] });
      resetForm();
      setIsCreateDialogOpen(false);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: FactorUpdate }) =>
      FactorsService.updateFactor({ factorId: id, requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["factors"] });
      resetForm();
      setEditingFactor(null);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => FactorsService.deleteFactor({ factorId: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["factors"] });
    },
  });

  const resetForm = () => {
    setFormName("");
    setFormExpression("");
    setFormDescription("");
    setFormType("feature");
  };

  const handleCreate = () => {
    // Labels are not user-creatable - they come from system config
    if (formType === "label") {
      alert(
        "Labels are configured in system_config.yaml and cannot be created manually.",
      );
      return;
    }

    const data: FactorCreate = {
      name: formName,
      expression: formExpression,
      description: formDescription,
      factor_type: formType,
    };
    createMutation.mutate(data);
  };

  const handleUpdate = () => {
    if (!editingFactor || !editingFactor.id) return;
    const data: FactorUpdate = {
      name: formName,
      expression: formExpression,
      description: formDescription,
    };
    updateMutation.mutate({ id: editingFactor.id, data });
  };

  const handleEdit = (factor: Factor) => {
    setEditingFactor(factor);
    setFormName(factor.name);
    setFormExpression(factor.expression);
    setFormDescription(factor.description || "");
    setFormType(factor.factor_type as "feature" | "label");
  };

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this factor?")) {
      deleteMutation.mutate(id);
    }
  };

  const error = featuresError || labelsError;

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                Factor Management
              </h1>
              <p className="text-muted-foreground">
                Manage features (X) and labels (Y) for model training
              </p>
            </div>
            <Dialog
              open={isCreateDialogOpen}
              onOpenChange={setIsCreateDialogOpen}
            >
              <DialogTrigger asChild>
                <Button onClick={() => resetForm()}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Factor
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                  <DialogTitle>Create New Factor</DialogTitle>
                  <DialogDescription>
                    Define a new factor using Qlib expression syntax
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={formName}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setFormName(e.target.value)
                      }
                      placeholder="e.g., ma5, rsi_14"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="type">Type</Label>
                    <Select
                      value={formType}
                      onValueChange={(v) =>
                        setFormType(v as "feature" | "label")
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="feature">Feature (X)</SelectItem>
                        <SelectItem value="label" disabled={true}>
                          Label (Y) - Configured in system_config.yaml
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    {formType === "label" && (
                      <p className="text-xs text-destructive">
                        Labels are configured in system_config.yaml based on
                        market region and cannot be created manually.
                      </p>
                    )}
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="expression">Expression</Label>
                    <Textarea
                      id="expression"
                      value={formExpression}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                        setFormExpression(e.target.value)
                      }
                      placeholder="e.g., Mean($close, 5) or Ref($close, -1) / $close - 1"
                      rows={3}
                    />
                    <p className="text-xs text-muted-foreground">
                      Use Qlib expression syntax. Examples: Mean($close, 5),
                      Std($volume, 10)
                    </p>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="description">Description (Optional)</Label>
                    <Input
                      id="description"
                      value={formDescription}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setFormDescription(e.target.value)
                      }
                      placeholder="Brief description of this factor"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setIsCreateDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={
                      !formName || !formExpression || createMutation.isPending
                    }
                  >
                    {createMutation.isPending ? (
                      <>
                        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      "Create"
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Factors
                </CardTitle>
                <Layers className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(features?.length || 0) +
                    (alpha158Info?.enabled
                      ? alpha158Info?.factor_count || 0
                      : 0) +
                    (labelConfig ? 1 : 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {features?.length || 0} data fields
                  {alpha158Info?.enabled
                    ? ` + ${alpha158Info?.factor_count} Alpha158`
                    : ""}
                  {labelConfig ? " + 1 label" : ""}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Features</CardTitle>
                <FlaskConical className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(features?.length || 0) +
                    (alpha158Info?.enabled
                      ? alpha158Info?.factor_count || 0
                      : 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {features
                    ?.filter((f) => (f as ExtendedFactor)._isBuiltin)
                    .map((f) => f.name.replace(/\.(day|1min)$/, ""))
                    .join(", ")}
                  {alpha158Info?.enabled
                    ? `, + ${alpha158Info?.factor_count} Alpha158 factors`
                    : ""}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Label (Target)
                </CardTitle>
                <Tag className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                {labelConfig ? (
                  <>
                    <p className="text-sm font-bold font-mono">
                      {labelConfig.expression}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {labelConfig.description}
                    </p>
                  </>
                ) : (
                  <>
                    <div className="text-2xl font-bold">0</div>
                    <p className="text-xs text-muted-foreground">
                      No label configured
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load factors: {(error as Error).message}
              </AlertDescription>
            </Alert>
          )}

          {/* Mutation Error */}
          {(createMutation.error ||
            updateMutation.error ||
            deleteMutation.error) && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {(createMutation.error as Error)?.message ||
                  (updateMutation.error as Error)?.message ||
                  (deleteMutation.error as Error)?.message}
              </AlertDescription>
            </Alert>
          )}

          {/* Tabs for Features and Labels */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="features">
                Features (
                {(features?.length || 0) +
                  (alpha158Info?.enabled ? alpha158Info?.factor_count || 0 : 0)}
                )
              </TabsTrigger>
              <TabsTrigger value="labels">
                Labels ({labelConfig ? 1 : 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="features" className="mt-4 space-y-6">
              {/* Alpha158 Built-in Factor Library */}
              {alpha158Info && (
                <Card className="border-blue-200 bg-blue-50/30">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Package className="h-5 w-5 text-blue-600" />
                        <CardTitle className="text-lg">
                          {alpha158Info.display_name}
                        </CardTitle>
                        {alpha158Info.enabled ? (
                          <Badge variant="default" className="bg-green-600">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Enabled
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <XCircle className="h-3 w-3 mr-1" />
                            Disabled
                          </Badge>
                        )}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setShowAlpha158Factors(!showAlpha158Factors)
                        }
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        {showAlpha158Factors ? "Hide" : "View"} Factors
                        {showAlpha158Factors ? (
                          <ChevronUp className="h-4 w-4 ml-1" />
                        ) : (
                          <ChevronDown className="h-4 w-4 ml-1" />
                        )}
                      </Button>
                    </div>
                    <CardDescription>
                      {alpha158Info.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>
                        <strong>{alpha158Info.factor_count}</strong> factors
                      </span>
                      <span>
                        Categories:{" "}
                        {Array.from(
                          new Set(alpha158Info.factors.map((f) => f.category)),
                        ).join(", ")}
                      </span>
                      <span>
                        Data: {alpha158Info.data_requirements.join(", ")}
                      </span>
                    </div>

                    {/* Alpha158 Factor List (Collapsible) */}
                    {showAlpha158Factors && (
                      <div className="mt-4 border rounded-lg overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-24">Name</TableHead>
                              <TableHead>Expression</TableHead>
                              <TableHead className="w-20">Category</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {alpha158Info.factors.map((factor) => (
                              <TableRow key={factor.name}>
                                <TableCell className="font-mono text-xs">
                                  {factor.name}
                                </TableCell>
                                <TableCell>
                                  <code className="text-xs bg-muted px-1 py-0.5 rounded break-all">
                                    {factor.expression}
                                  </code>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="outline" className="text-xs">
                                    {factor.category}
                                  </Badge>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}

                    <p className="text-xs text-muted-foreground mt-3">
                      Configure in <code>system_config.yaml</code> →{" "}
                      <code>builtin_factor_libraries.alpha158.enabled</code>
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Custom Factors Table */}
              <FactorTable
                factors={features || []}
                isLoading={featuresLoading}
                onEdit={handleEdit}
                onDelete={handleDelete}
                type="feature"
              />
            </TabsContent>

            <TabsContent value="labels" className="mt-4">
              {/* Label Configuration (from system_config.yaml) */}
              {labelsLoading ? (
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-center">
                      <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span className="ml-2 text-muted-foreground">
                        Loading...
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ) : labelConfig ? (
                <Card className="border-green-200 bg-green-50/30">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Tag className="h-5 w-5 text-green-600" />
                      <CardTitle>Label Configuration</CardTitle>
                      <Badge variant="outline" className="ml-2">
                        Region: {labelConfig.region.toUpperCase()}
                      </Badge>
                    </div>
                    <CardDescription>
                      Target variable (Y) for model training - configured based
                      on market region
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Name</TableHead>
                          <TableHead>Expression</TableHead>
                          <TableHead>Description</TableHead>
                          <TableHead className="text-right">Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <TableRow>
                          <TableCell className="font-medium">
                            {labelConfig.name}
                          </TableCell>
                          <TableCell>
                            <code className="text-xs bg-muted px-2 py-1 rounded">
                              {labelConfig.expression}
                            </code>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {labelConfig.description}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className="inline-flex items-center text-muted-foreground text-xs">
                              <Lock className="h-3 w-3 mr-1" />
                              System Config
                            </span>
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                    <p className="text-xs text-muted-foreground mt-4">
                      Labels are determined by market region and cannot be
                      modified manually. Configure in{" "}
                      <code>system_config.yaml</code> →{" "}
                      <code>label_config</code>
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-6">
                    <div className="text-center text-muted-foreground">
                      <Tag className="mx-auto h-12 w-12 mb-4 opacity-50" />
                      <p>No label configuration found.</p>
                      <p className="text-sm mt-2">
                        Check system_config.yaml for label_config settings.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>

          {/* Edit Dialog */}
          <Dialog
            open={editingFactor !== null}
            onOpenChange={(open) => !open && setEditingFactor(null)}
          >
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Edit Factor</DialogTitle>
                <DialogDescription>Update factor definition</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="edit-name">Name</Label>
                  <Input
                    id="edit-name"
                    value={formName}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setFormName(e.target.value)
                    }
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="edit-expression">Expression</Label>
                  <Textarea
                    id="edit-expression"
                    value={formExpression}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                      setFormExpression(e.target.value)
                    }
                    rows={3}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="edit-description">Description</Label>
                  <Input
                    id="edit-description"
                    value={formDescription}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setFormDescription(e.target.value)
                    }
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setEditingFactor(null)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUpdate}
                  disabled={
                    !formName || !formExpression || updateMutation.isPending
                  }
                >
                  {updateMutation.isPending ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </div>
  );
}

// Extended Factor type with builtin flag
interface ExtendedFactor extends Factor {
  _isBuiltin?: boolean;
}

// Factor Table Component
interface FactorTableProps {
  factors: ExtendedFactor[];
  isLoading: boolean;
  onEdit: (factor: ExtendedFactor) => void;
  onDelete: (id: string) => void;
  type: "feature" | "label";
}

function FactorTable({
  factors,
  isLoading,
  onEdit,
  onDelete,
  type,
}: FactorTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (factors.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            <FlaskConical className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No {type === "feature" ? "features" : "labels"} defined yet.</p>
            <p className="text-sm mt-2">
              Click "Create Factor" to add your first {type}.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{type === "feature" ? "Features" : "Labels"}</CardTitle>
        <CardDescription>
          {type === "feature"
            ? "Input variables used for model training"
            : "Target variables the model will predict"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Expression</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {factors.map((factor) => (
              <TableRow key={factor.id}>
                <TableCell className="font-medium">{factor.name}</TableCell>
                <TableCell>
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {factor.expression}
                  </code>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      factor.status === "active" ? "default" : "secondary"
                    }
                  >
                    {factor.status?.toUpperCase() || "ACTIVE"}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {factor.description || "-"}
                </TableCell>
                <TableCell className="text-right">
                  {(factor as ExtendedFactor)._isBuiltin ? (
                    <span className="inline-flex items-center text-muted-foreground text-xs">
                      <Lock className="h-3 w-3 mr-1" />
                      Built-in
                    </span>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onEdit(factor)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => factor.id && onDelete(factor.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
