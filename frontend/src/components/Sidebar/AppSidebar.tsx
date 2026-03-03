import {
  Home,
  Users,
  Brain,
  Database,
  FlaskConical,
  TrendingUp,
  RefreshCw,
} from "lucide-react";

import { SidebarAppearance } from "@/components/Common/Appearance";
import { Logo } from "@/components/Common/Logo";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";
import useAuth from "@/hooks/useAuth";
import { type Item, Main } from "./Main";
import { User } from "./User";

const baseItems: Item[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: FlaskConical, title: "Factors", path: "/factors" },
  { icon: Database, title: "Data Sources", path: "/data-sources" },
  { icon: Brain, title: "Model", path: "/models" },
  { icon: TrendingUp, title: "Backtest", path: "/backtest" },
  { icon: RefreshCw, title: "Routine", path: "/routine" },
  // Paper Trading 已移除 - 执行层委托给 VeighNa/LEAN
];

export function AppSidebar() {
  const { user: currentUser } = useAuth();

  const items = currentUser?.is_superuser
    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
    : baseItems;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  );
}

export default AppSidebar;
