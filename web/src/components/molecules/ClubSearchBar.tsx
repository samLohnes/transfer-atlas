import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { searchClubs } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import { Spinner } from "@/components/atoms/Spinner";
import type { ClubSearchResult } from "@/types/club";

interface ClubSearchBarProps {
  className?: string;
}

/** Text input with autocomplete dropdown — frosted glass style. */
export function ClubSearchBar({ className = "" }: ClubSearchBarProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ClubSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults([]);
      return;
    }
    setIsLoading(true);
    searchClubs(debouncedQuery)
      .then((res) => {
        setResults(res.clubs);
        setIsOpen(true);
      })
      .catch(() => setResults([]))
      .finally(() => setIsLoading(false));
  }, [debouncedQuery]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(club: ClubSearchResult) {
    setQuery("");
    setIsOpen(false);
    navigate(`/network/${club.club_id}`);
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative group">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6b8a78] transition-colors group-focus-within:text-[#4ade80]" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="Search clubs..."
          className="w-full rounded-xl bg-white/[0.03] border border-white/[0.06] pl-10 pr-4 py-2.5 text-[13px] text-[#e8f0ec] placeholder-[#4a6555] focus:outline-none focus:border-[#4ade80]/30 focus:bg-white/[0.05] focus:shadow-[0_0_20px_rgba(74,222,128,0.08)] transition-all duration-200"
        />
        {isLoading && <Spinner size="sm" className="absolute right-3.5 top-1/2 -translate-y-1/2" />}
      </div>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-full rounded-xl bg-[#0e1f16]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_16px_48px_rgba(0,0,0,0.5)] max-h-64 overflow-y-auto">
          {query.length < 2 ? (
            <div className="px-4 py-3.5 text-[13px] text-[#4a6555]">Type at least 2 characters</div>
          ) : results.length === 0 ? (
            <div className="px-4 py-3.5 text-[13px] text-[#4a6555]">No results</div>
          ) : (
            results.map((club, i) => (
              <button
                key={club.club_id}
                onClick={() => handleSelect(club)}
                className={`w-full text-left px-4 py-2.5 hover:bg-white/[0.04] transition-colors ${i > 0 ? "border-t border-white/[0.04]" : ""}`}
              >
                <div className="text-[13px] font-medium text-[#e8f0ec]">{club.club_name}</div>
                <div className="text-[11px] text-[#4a6555] mt-0.5">
                  {club.country_name}
                  {club.league_name && <span className="text-white/10 mx-1">·</span>}
                  {club.league_name && <span>{club.league_name}</span>}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
