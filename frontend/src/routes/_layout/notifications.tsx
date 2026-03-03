import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Mail,
  Plus,
  Trash2,
  Send,
  CheckCircle2,
  XCircle,
  Loader2,
  Settings,
  Bell,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { OpenAPI } from "@/client";
import { toast } from "sonner";
import { useState } from "react";

// API helper functions
const apiHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

async function fetchNotificationConfig() {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/config`,
    { headers: apiHeaders() },
  );
  if (!response.ok) throw new Error("Failed to fetch notification config");
  return response.json();
}

async function updateNotificationConfig(config: {
  enabled?: boolean;
  recipients?: string[];
}) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/config`,
    {
      method: "PUT",
      headers: apiHeaders(),
      body: JSON.stringify(config),
    },
  );
  if (!response.ok) throw new Error("Failed to update notification config");
  return response.json();
}

async function addRecipient(email: string) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/recipient`,
    {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({ email }),
    },
  );
  if (!response.ok) throw new Error("Failed to add recipient");
  return response.json();
}

async function removeRecipient(email: string) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/recipient/${encodeURIComponent(email)}`,
    {
      method: "DELETE",
      headers: apiHeaders(),
    },
  );
  if (!response.ok) throw new Error("Failed to remove recipient");
  return response.json();
}

async function sendTestEmail(recipient?: string) {
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/paper-trading/notification/test`,
    {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({ recipient }),
    },
  );
  if (!response.ok) throw new Error("Failed to send test email");
  return response.json();
}

export const Route = createFileRoute("/_layout/notifications")({
  component: NotificationsPage,
  head: () => ({
    meta: [{ title: "Notifications - QuantBot" }],
  }),
});

function NotificationsPage() {
  const queryClient = useQueryClient();
  const [newEmail, setNewEmail] = useState("");

  // Query for notification config
  const {
    data: configData,
    isLoading: configLoading,
    error: configError,
  } = useQuery({
    queryKey: ["notificationConfig"],
    queryFn: fetchNotificationConfig,
  });

  // Mutation for updating config
  const updateConfigMutation = useMutation({
    mutationFn: updateNotificationConfig,
    onSuccess: (response) => {
      if (response.success) {
        toast.success("Configuration updated");
        queryClient.invalidateQueries({ queryKey: ["notificationConfig"] });
      } else {
        toast.error(response.error || "Failed to update configuration");
      }
    },
    onError: (error) => {
      toast.error(`Failed to update configuration: ${error.message}`);
    },
  });

  // Mutation for adding recipient
  const addRecipientMutation = useMutation({
    mutationFn: addRecipient,
    onSuccess: (response) => {
      if (response.success) {
        toast.success("Recipient added");
        setNewEmail("");
        queryClient.invalidateQueries({ queryKey: ["notificationConfig"] });
      } else {
        toast.error(response.error || "Failed to add recipient");
      }
    },
    onError: (error) => {
      toast.error(`Failed to add recipient: ${error.message}`);
    },
  });

  // Mutation for removing recipient
  const removeRecipientMutation = useMutation({
    mutationFn: removeRecipient,
    onSuccess: (response) => {
      if (response.success) {
        toast.success("Recipient removed");
        queryClient.invalidateQueries({ queryKey: ["notificationConfig"] });
      } else {
        toast.error(response.error || "Failed to remove recipient");
      }
    },
    onError: (error) => {
      toast.error(`Failed to remove recipient: ${error.message}`);
    },
  });

  // Mutation for sending test email
  const sendTestMutation = useMutation({
    mutationFn: sendTestEmail,
    onSuccess: (response) => {
      if (response.success) {
        toast.success(response.message || "Test email sent");
      } else {
        toast.error(response.error || "Failed to send test email");
      }
    },
    onError: (error) => {
      toast.error(`Failed to send test email: ${error.message}`);
    },
  });

  const config = configData?.config;
  const isEnabled = config?.enabled ?? false;
  const recipients = config?.recipients ?? [];

  const handleToggleEnabled = () => {
    updateConfigMutation.mutate({ enabled: !isEnabled });
  };

  const handleAddRecipient = (e: React.FormEvent) => {
    e.preventDefault();
    if (newEmail.trim() && newEmail.includes("@")) {
      addRecipientMutation.mutate(newEmail.trim());
    } else {
      toast.error("Please enter a valid email address");
    }
  };

  const handleRemoveRecipient = (email: string) => {
    removeRecipientMutation.mutate(email);
  };

  const handleSendTest = () => {
    if (recipients.length === 0) {
      toast.error("Please add at least one recipient first");
      return;
    }
    sendTestMutation.mutate(undefined);
  };

  return (
    <div className="flex flex-col overflow-hidden -m-6 md:-m-8 h-[calc(100vh-8rem)]">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="space-y-6">
          {/* Page Header */}
          <div>
            <h1 className="text-2xl font-bold">Email Notifications</h1>
            <p className="text-muted-foreground">
              Configure email notifications for daily trading reports
            </p>
          </div>

          {/* Status Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-blue-500" />
                  <CardTitle className="text-lg">Notification Status</CardTitle>
                </div>
                {configLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : isEnabled ? (
                  <Badge className="bg-green-500">Enabled</Badge>
                ) : (
                  <Badge variant="secondary">Disabled</Badge>
                )}
              </div>
              <CardDescription>
                When enabled, you will receive daily trading reports via email
                after each routine execution.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {configError ? (
                <div className="flex items-center gap-2 text-red-500">
                  <XCircle className="h-4 w-4" />
                  <span>Failed to load configuration</span>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={isEnabled}
                      onCheckedChange={handleToggleEnabled}
                      disabled={updateConfigMutation.isPending}
                    />
                    <Label>
                      {isEnabled
                        ? "Notifications are enabled"
                        : "Notifications are disabled"}
                    </Label>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSendTest}
                    disabled={
                      sendTestMutation.isPending ||
                      !isEnabled ||
                      recipients.length === 0
                    }
                  >
                    {sendTestMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Send Test Email
                      </>
                    )}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recipients Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-purple-500" />
                <CardTitle className="text-lg">Email Recipients</CardTitle>
              </div>
              <CardDescription>
                Add email addresses to receive trading reports. Reports include
                the target portfolio with all stock weights and deviations.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add recipient form */}
              <form onSubmit={handleAddRecipient} className="flex gap-2">
                <Input
                  type="email"
                  placeholder="Enter email address..."
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="submit"
                  disabled={addRecipientMutation.isPending || !newEmail.trim()}
                >
                  {addRecipientMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-1" />
                      Add
                    </>
                  )}
                </Button>
              </form>

              {/* Recipients list */}
              {recipients.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <Mail className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recipients configured</p>
                  <p className="text-sm">
                    Add an email address to receive trading reports
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {recipients.map((email: string) => (
                    <div
                      key={email}
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                    >
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <span>{email}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveRecipient(email)}
                        disabled={removeRecipientMutation.isPending}
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* SMTP Configuration Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-gray-500" />
                <CardTitle className="text-lg">SMTP Configuration</CardTitle>
              </div>
              <CardDescription>
                SMTP settings are configured via environment variables in .env
                file.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {configLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading...
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-muted-foreground">SMTP Host</Label>
                    <div className="font-mono mt-1">
                      {config?.smtp_host || "Not configured"}
                    </div>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">SMTP Port</Label>
                    <div className="font-mono mt-1">
                      {config?.smtp_port || "Not configured"}
                    </div>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">SMTP User</Label>
                    <div className="font-mono mt-1">
                      {config?.smtp_user || "Not configured"}
                    </div>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">From Email</Label>
                    <div className="font-mono mt-1">
                      {config?.from_email || "Not configured"}
                    </div>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">TLS</Label>
                    <div className="mt-1">
                      {config?.smtp_tls ? (
                        <Badge variant="outline" className="text-green-600">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Enabled
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-gray-500">
                          Disabled
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">From Name</Label>
                    <div className="font-mono mt-1">
                      {config?.from_name || "QuantBot"}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
            <CardContent className="pt-6">
              <div className="flex gap-3">
                <Mail className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-blue-700 dark:text-blue-400">
                    About Email Reports
                  </p>
                  <p className="text-blue-600 dark:text-blue-300 mt-1">
                    After each routine execution, an email report will be sent
                    containing:
                  </p>
                  <ul className="list-disc list-inside text-blue-600 dark:text-blue-300 mt-2 space-y-1">
                    <li>Portfolio summary (benchmark, total stocks, etc.)</li>
                    <li>Top 20 overweight positions</li>
                    <li>Top 20 underweight positions</li>
                    <li>Execution time and duration</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
