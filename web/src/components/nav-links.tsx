"use client";

import { History, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/history", label: "History", Icon: History },
  { href: "/", label: "New brief", Icon: Plus },
] as const;

/** On phones: 44px icon buttons (labels for screen readers) so the brand keeps its size. */
export function NavLinks() {
  const path = usePathname();
  return (
    <div className="flex shrink-0 items-center gap-1">
      {LINKS.map(({ href, label, Icon }) => {
        const current = href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "flex h-11 min-w-11 items-center justify-center gap-1.5 rounded-lg px-2.5 text-sm font-medium outline-none hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/30",
              current ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon aria-hidden className="size-4.5" />
            <span className="sr-only sm:not-sr-only">{label}</span>
          </Link>
        );
      })}
    </div>
  );
}
