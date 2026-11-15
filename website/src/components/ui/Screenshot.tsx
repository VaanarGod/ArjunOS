import { useState } from 'react'
import { Image as ImageIcon } from 'lucide-react'

export default function Screenshot({
  file,
  alt,
  className = '',
}: {
  file: string
  alt: string
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  const src = `./images/${file}`

  if (failed) {
    return (
      <div
        className={`flex aspect-[16/10] items-center justify-center rounded-xl border border-dashed border-cyan/25 bg-gradient-to-br from-midnight via-void to-navy ${className}`}
      >
        <div className="px-4 text-center">
          <ImageIcon className="mx-auto mb-2 h-8 w-8 text-cyan/40" />
          <p className="text-xs text-gray-500">Drop your screenshot here:</p>
          <p className="mt-1 font-mono text-[11px] text-cyan/70">
            public/images/{file}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`overflow-hidden rounded-xl border border-cyan/10 bg-void ${className}`}>
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onError={() => setFailed(true)}
        className="block h-full w-full object-cover"
      />
    </div>
  )
}
