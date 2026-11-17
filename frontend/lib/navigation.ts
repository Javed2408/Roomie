import {
  Building2,
  Compass,
  Heart,
  House,
  MessageCircle,
  User,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  /** A shorter label for the narrow mobile bar. Defaults to `label`. */
  shortLabel?: string;
  icon: LucideIcon;
  /**
   * The mobile bottom bar holds at most five items, the most that stay
   * comfortably tappable on a phone. Anything else is reached from the
   * profile menu in the header.
   */
  inBottomNav: boolean;
}

/** The main sections of the signed-in app, in display order. */
export const APP_NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Home", icon: House, inBottomNav: true },
  { href: "/discover", label: "Discover", icon: Compass, inBottomNav: true },
  { href: "/matches", label: "Matches", icon: Heart, inBottomNav: true },
  {
    href: "/messages",
    label: "Messages",
    icon: MessageCircle,
    inBottomNav: true,
  },
  {
    href: "/accommodation",
    label: "Accommodation",
    shortLabel: "Housing",
    icon: Building2,
    inBottomNav: true,
  },
  { href: "/profile", label: "Profile", icon: User, inBottomNav: false },
];

/** True when `pathname` is the item's page or a page beneath it. */
export function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
