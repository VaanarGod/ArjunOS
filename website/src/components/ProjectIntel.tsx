import { useEffect, useState } from 'react'
import { Star, GitFork, AlertCircle, GitBranch, Clock, Loader2, RefreshCw } from 'lucide-react'
import { API_URL, REPO_URL } from '../data/content'

export default function ProjectIntel() {
  const [data, setData] = useState<any>(null)
  const [release, setRelease] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await fetch(API_URL)
      if (!res.ok) throw new Error()
      const repoData = await res.json()
      
      const relRes = await fetch(`${API_URL}/releases/latest`)
      const relData = relRes.ok ? await relRes.json() : null

      setData(repoData)
      setRelease(relData)
    } catch (e) {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Cache in sessionStorage for 10 minutes to avoid rate limits
    const cached = sessionStorage.getItem('arjunos_github')
    if (cached) {
      const parsed = JSON.parse(cached)
      if (Date.now() - parsed.time < 600000) {
        setData(parsed.data)
        setRelease(parsed.release)
        setLoading(false)
        return
      }
    }
    fetchData().then(() => {
      if (data && release) {
        sessionStorage.setItem('arjunos_github', JSON.stringify({ time: Date.now(), data, release }))
      }
    })
  }, []) // eslint-disable-line

  return (
    <div className="glass rounded-3xl p-6 md:p-8 mt-12 border border-white/5 bg-[#050505]/95">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
            <GitBranch className="text-cyan w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Live Project Intelligence</h3>
            <p className="text-xs text-gray-500">Synced via GitHub API</p>
          </div>
        </div>
        <button onClick={() => { sessionStorage.removeItem('arjunos_github'); fetchData(); }} disabled={loading} className="p-2 rounded-lg border border-white/10 text-gray-400 hover:text-cyan disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32 text-cyan/50"><Loader2 className="animate-spin" /></div>
      ) : error ? (
        <div className="text-center text-sm text-red-400 py-8">Failed to load repository data. GitHub rate limit may be exceeded.</div>
      ) : data && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Stars</p>
            <p className="text-2xl font-display text-white">{data.stargazers_count}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Forks</p>
            <p className="text-2xl font-display text-white">{data.forks_count}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Open Issues</p>
            <p className="text-2xl font-display text-white">{data.open_issues_count}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Latest Release</p>
            {release ? (
              <a href={release.html_url} target="_blank" rel="noreferrer" className="text-2xl font-display text-cyan hover:text-ice block truncate">
                {release.tag_name}
              </a>
            ) : (
              <p className="text-xl font-display text-gray-500">None</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
