import { Map } from "lucide-react";

/** Placeholder for the Map view — built in Task 6. */
export function MapPage() {
  return (
    <div className="flex-1 flex items-center justify-center text-[#8fa898]">
      <div className="text-center">
        <Map className="h-16 w-16 mx-auto mb-4 opacity-30" />
        <p className="text-lg">Map View</p>
        <p className="text-sm mt-1">Geographic transfer flow visualization</p>
      </div>
    </div>
  );
}
