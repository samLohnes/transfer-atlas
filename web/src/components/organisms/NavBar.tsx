import { NavLink } from "react-router-dom";
import { Map, Network } from "lucide-react";
import { FreshnessBadge } from "@/components/molecules/FreshnessBadge";

/** Top navigation bar with logo, view switcher, and freshness badge. */
export function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? "bg-[#243d2e] text-[#4ade80]"
        : "text-[#8fa898] hover:text-[#e8f0ec] hover:bg-[#243d2e]/50"
    }`;

  return (
    <nav className="h-12 flex items-center justify-between px-4 bg-[#1a2e22] border-b border-[#2d4a38] shrink-0">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold text-[#4ade80] tracking-tight">TransferAtlas</span>
      </div>

      <div className="flex items-center gap-1">
        <NavLink to="/" className={linkClass} end>
          <Map className="h-4 w-4" />
          Map
        </NavLink>
        <NavLink to="/network" className={linkClass}>
          <Network className="h-4 w-4" />
          Network
        </NavLink>
      </div>

      <div className="flex items-center">
        <FreshnessBadge />
      </div>
    </nav>
  );
}
