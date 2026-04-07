export function LoadingSpinner({ size = 28 }: { size?: number }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div
        className="animate-spin rounded-full border-2 border-slate-700 border-t-accent-teal"
        style={{ width: size, height: size }}
      />
    </div>
  );
}
