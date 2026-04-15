import { useParams } from "react-router-dom";
import { Network } from "lucide-react";
import { ClubSearchBar } from "@/components/molecules/ClubSearchBar";

/** Placeholder for the Network Graph view — built in Task 8. */
export function NetworkGraphPage() {
  const { clubId } = useParams<{ clubId: string }>();

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex justify-center py-4">
        <ClubSearchBar className="w-96" />
      </div>
      <div className="flex-1 flex items-center justify-center text-[#8fa898]">
        <div className="text-center">
          <Network className="h-16 w-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg">Network Graph View</p>
          <p className="text-sm mt-1">
            {clubId ? `Club ID: ${clubId}` : "Search for a club above to explore its transfer network"}
          </p>
        </div>
      </div>
    </div>
  );
}
