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
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { FactorsService, DataSourceService } from "@/client";
import type { Factor, FactorCreate, FactorUpdate } from "@/client";

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

  // Form state for create/edit
  const [formName, setFormName] = useState("");
  const [formExpression, setFormExpression] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formType, setFormType] = useState<"feature" | "label">("feature");

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

  // Query for labels
  const {
    data: labels,
    isLoading: labelsLoading,
    error: labelsError,
  } = useQuery({
    queryKey: ["factors", "label"],
    queryFn: () => FactorsService.getFactors({ factorType: "label" }),
  });

  // OHLCV base field names (without frequency suffix)
  const OHLCV_FIELDS = ["close", "open", "high", "low", "volume"];

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
      description: "Built-in OHLCV field",
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
    // Check if trying to create a label when one already exists
    if (formType === "label" && labels && labels.length > 0) {
      alert(
        "Only one label is allowed. Please edit the existing label instead.",
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
                        <SelectItem
                          value="label"
                          disabled={labels && labels.length > 0}
                        >
                          Label (Y){" "}
                          {labels && labels.length > 0 && "(Already exists)"}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    {formType === "label" && labels && labels.length > 0 && (
                      <p className="text-xs text-destructive">
                        Only one label is allowed. Please edit the existing
                        label instead.
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
                  {(features?.length || 0) + (labels?.length || 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  Features + Labels combined
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
                  {features?.length || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Input variables (X) for training
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Labels</CardTitle>
                <Tag className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{labels?.length || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Target variable (Y) to predict
                </p>
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
                Features ({features?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="labels">
                Labels ({labels?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="features" className="mt-4">
              <FactorTable
                factors={features || []}
                isLoading={featuresLoading}
                onEdit={handleEdit}
                onDelete={handleDelete}
                type="feature"
              />
            </TabsContent>

            <TabsContent value="labels" className="mt-4">
              <FactorTable
                factors={labels || []}
                isLoading={labelsLoading}
                onEdit={handleEdit}
                onDelete={handleDelete}
                type="label"
              />
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
