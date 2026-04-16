import { NavLink } from "react-router-dom";
import { Map, Network, User } from "lucide-react";
import { FreshnessBadge } from "@/components/molecules/FreshnessBadge";

/** Top navigation bar with glass-morphism effect. */
export function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-[13px] font-medium tracking-wide transition-all duration-200 ${
      isActive
        ? "bg-[#4ade80]/10 text-[#4ade80] shadow-[inset_0_0_0_1px_rgba(74,222,128,0.2)]"
        : "text-[#6b8a78] hover:text-[#c5dace] hover:bg-white/[0.03]"
    }`;

  return (
    <nav className="h-12 flex items-center justify-between px-5 bg-[#0e1f16]/80 backdrop-blur-xl border-b border-white/[0.06] shrink-0 relative noise">
      <div className="flex items-center gap-2.5">
        <div className="w-6 h-6 rounded-md bg-gradient-to-br from-[#4ade80] to-[#22c55e] flex items-center justify-center shadow-[0_0_12px_rgba(74,222,128,0.2)]">
          <span className="text-[10px] font-bold text-[#0a1410] leading-none tracking-tight">TA</span>
        </div>
        <span className="text-[15px] font-semibold text-[#c5dace] tracking-tight">
          Transfer<span className="text-[#4ade80]">Atlas</span>
        </span>
      </div>

      <div className="flex items-center gap-1 bg-white/[0.02] rounded-lg p-0.5 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)]">
        <NavLink to="/" className={linkClass} end>
          <Map className="h-3.5 w-3.5" />
          Map
        </NavLink>
        <NavLink to="/network" className={linkClass}>
          <Network className="h-3.5 w-3.5" />
          Network
        </NavLink>
        <NavLink to="/players" className={linkClass}>
          <User className="h-3.5 w-3.5" />
          Players
        </NavLink>
      </div>

      <div className="flex items-center">
        <FreshnessBadge />
      </div>
    </nav>
  );
}
