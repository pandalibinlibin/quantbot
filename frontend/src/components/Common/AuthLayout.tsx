import { Link, useLocation } from "@tanstack/react-router";
import { Appearance } from "@/components/Common/Appearance";
import { Logo } from "@/components/Common/Logo";
import { Button } from "@/components/ui/button";
import { Footer } from "./Footer";

interface AuthLayoutProps {
  children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  const location = useLocation();
  const isLoginPage = location.pathname === "/login";

  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="bg-muted dark:bg-zinc-900 relative hidden lg:flex lg:items-center lg:justify-center">
        <Logo variant="full" className="h-16" asLink={false} />
      </div>
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex items-center justify-end gap-2">
          {isLoginPage ? (
            <Button variant="outline" size="sm" asChild>
              <Link to="/signup">Sign Up</Link>
            </Button>
          ) : (
            <Button variant="outline" size="sm" asChild>
              <Link to="/login">Log In</Link>
            </Button>
          )}
          <Appearance />
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  );
}
