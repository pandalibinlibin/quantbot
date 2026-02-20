import { Link } from "@tanstack/react-router";

import { cn } from "@/lib/utils";

interface LogoProps {
  variant?: "full" | "icon" | "responsive";
  className?: string;
  asLink?: boolean;
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <span
          className={cn(
            "text-2xl font-bold text-primary group-data-[collapsible=icon]:hidden",
            className,
          )}
        >
          Quantbot
        </span>
        <span
          className={cn(
            "text-2xl font-bold text-primary hidden group-data-[collapsible=icon]:block",
            className,
          )}
        >
          Q
        </span>
      </>
    ) : (
      <span
        className={cn(
          variant === "full"
            ? "text-2xl font-bold text-primary"
            : "text-2xl font-bold text-primary",
          className,
        )}
      >
        {variant === "full" ? "Quantbot" : "Q"}
      </span>
    );

  if (!asLink) {
    return content;
  }

  return <Link to="/">{content}</Link>;
}
