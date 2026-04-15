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

/** Text input with autocomplete dropdown for club search. */
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
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#8fa898]" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="Search clubs..."
          className="w-full rounded-md bg-[#243d2e] border border-[#2d4a38] pl-10 pr-4 py-2 text-sm text-[#e8f0ec] placeholder-[#8fa898] focus:outline-none focus:border-[#4ade80]"
        />
        {isLoading && <Spinner size="sm" className="absolute right-3 top-1/2 -translate-y-1/2" />}
      </div>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-md bg-[#1e3a2a] border border-[#2d4a38] shadow-lg max-h-60 overflow-y-auto">
          {query.length < 2 ? (
            <div className="px-4 py-3 text-sm text-[#8fa898]">Type at least 2 characters</div>
          ) : results.length === 0 ? (
            <div className="px-4 py-3 text-sm text-[#8fa898]">No results</div>
          ) : (
            results.map((club) => (
              <button
                key={club.club_id}
                onClick={() => handleSelect(club)}
                className="w-full text-left px-4 py-2 hover:bg-[#243d2e] transition-colors"
              >
                <div className="text-sm text-[#e8f0ec]">{club.club_name}</div>
                <div className="text-xs text-[#8fa898]">
                  {club.country_name}
                  {club.league_name && ` · ${club.league_name}`}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
