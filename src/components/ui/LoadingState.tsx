import { Loader2 } from 'lucide-react';

export default function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center py-12 gap-2 text-sm text-gray-500">
      <Loader2 size={16} className="animate-spin text-emerald-500" />
      {message}
    </div>
  );
}
