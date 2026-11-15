export default function StatusBadge({ status }: { status: string }) {
  const isPlanned = status.toLowerCase().includes('planned')
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${
        isPlanned ? 'bg-violet/10 text-violet' : 'bg-cyan/10 text-cyan'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isPlanned ? 'bg-violet' : 'bg-cyan'}`} />
      {status}
    </span>
  )
}
