export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div
        className="animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600"
        style={{ width: size, height: size }}
      />
    </div>
  );
}
