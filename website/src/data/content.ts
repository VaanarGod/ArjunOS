export const APP_NAME = 'ArjunOS'
export const APP_VERSION = '0.1.0'
export const APP_STATUS = 'Early build'
export const MIN_MACOS = 'macOS 14 (Sonoma) or later'
export const LICENSE = 'Apache-2.0'

// Real repository links
export const REPO_URL = 'https://github.com/VaanarGod/ArjunOS'
export const RELEASES_URL = `${REPO_URL}/releases`
export const DOCS_URL = `${REPO_URL}/tree/main/docs`
export const LICENSE_URL = `${REPO_URL}/blob/main/LICENSE`

// Direct download link for the latest release asset
export const DOWNLOAD_URL = `${REPO_URL}/releases/latest/download/ArjunOS-0.1.0.dmg`

export const techStack = [
  { label: 'macOS 14+', value: 'Native SwiftUI app' },
  { label: 'Swift 5.9', value: 'JarvisCore · JarvisOS' },
  { label: 'Python 3.11+', value: 'FastAPI bridge' },
  { label: 'Apache-2.0', value: 'Open source' },
] as const

export const features = [
  {
    id: 'local-chat',
    title: 'Local chat',
    description: 'Streams from models you already run: Ollama, LM Studio, llama.cpp, vLLM, or any OpenAI-compatible server. Models are discovered automatically and a default is chosen for you.',
    status: 'Implemented',
    icon: 'MessageSquare',
  },
  {
    id: 'crew',
    title: 'Crew',
    description: 'A boss model splits a job (for example, several PDFs) between small worker models, each with its own browser panel. Free RAM decides who is awake, or choose "boss sleeps, several workers at once".',
    status: 'Implemented',
    icon: 'Users',
  },
  {
    id: 'browser',
    title: 'Built-in browser',
    description: 'Tabs, downloads, popups, camera/mic prompts. Ask about the page you have open; it is read as the primary source.',
    status: 'Implemented',
    icon: 'Globe',
  },
  {
    id: 'web-search',
    title: 'Web search',
    description: 'DuckDuckGo, no key required. Asks permission first; only a short query is ever sent, never your chat.',
    status: 'Implemented',
    icon: 'Search',
  },
  {
    id: 'memory',
    title: 'Memory',
    description: 'Say "remember …". Notes live in local SQLite (FTS5), are all listed when you open the screen, can be undone, and never store secrets.',
    status: 'Implemented',
    icon: 'Database',
  },
  {
    id: 'profile',
    title: 'Profile',
    description: 'Tell it what to call you (asked once at first launch), set how you like answers, and write your own standing instructions. Compiled to ~40–70 tokens and capped at 1,600 characters.',
    status: 'Implemented',
    icon: 'UserRound',
  },
  {
    id: 'mcp',
    title: 'MCP tools',
    description: 'Connect Model Context Protocol servers with one JSON file per server to extend the assistant with additional tools.',
    status: 'Implemented',
    icon: 'Plug',
  },
  {
    id: 'files',
    title: 'Any file',
    description: 'Attach a file, or just write its path in a message. Text, code, PDF, Word, Excel, PowerPoint, OpenDocument, RTF, EPUB, SQLite, archives, images (vision models) and more.',
    status: 'Implemented',
    icon: 'FileText',
  },
  {
    id: 'obsidian',
    title: 'Obsidian',
    description: 'Connect a vault so the model can search it and add notes to its own folder. It never edits your notes.',
    status: 'Implemented',
    icon: 'BookOpen',
  },
  {
    id: 'floating',
    title: 'Floating assistant',
    description: 'A pet and mini chat above your other windows, opened with a global shortcut. Supports Codex-format pets.',
    status: 'Implemented',
    icon: 'Sparkles',
  },
  {
    id: 'terminal',
    title: 'Sandboxed terminal',
    description: 'A short allow-list of commands, each run only after you approve it. node also runs under macOS Seatbelt. Never allowed: sudo, su, rm, pipes, redirects, &&.',
    status: 'Implemented',
    icon: 'Terminal',
  },
  {
    id: 'create-files',
    title: 'Create files',
    description: 'Ask it to write a file and it does so in the workspace folder, never overwriting your existing files.',
    status: 'Implemented',
    icon: 'FolderPlus',
  },
  {
    id: 'rich-answers',
    title: 'Rich answers',
    description: 'Markdown, tables, code with Copy, and math (KaTeX), all rendered offline.',
    status: 'Implemented',
    icon: 'Palette',
  },
  {
    id: 'security',
    title: 'Local-first security',
    description: 'Loopback only, per-launch bearer token, one approval per action, sandboxed terminal, credential stores never read, untrusted page text fenced as data.',
    status: 'Design principle',
    icon: 'Shield',
  },
] as const

export const roadmap = [
  'Computer use — Swift side not yet compiled and verified by the author',
  'Voice — speech-to-text and text-to-speech',
  'Scheduled jobs and routines',
  'Plugins and skills',
  'First-run setup wizard',
  'Knowledge-base indexing of whole folders',
  'Cloud providers (deliberately blocked today)',
] as const

export const screenshots = [
  { file: 'screenshot-chat.png', title: 'Chat', description: 'The main conversation surface, streaming from your local model. Markdown, tables, code and math render offline.' },
  { file: 'screenshot-crew.png', title: 'Crew', description: 'A boss model orchestrates workers, each with its own browser panel. Free RAM decides how many run at once.' },
  { file: 'screenshot-browser.png', title: 'Built-in browser', description: 'Ask about the page you have open — it is read as the primary source, with page text fenced as untrusted data.' },
  { file: 'screenshot-memory.png', title: 'Memory', description: 'Local SQLite with full-text search. Memories are listed, undoable, and never store credentials.' },
  { file: 'screenshot-profile.png', title: 'Profile', description: 'Name, answer style dropdowns, standing instructions, and a live token meter showing exactly what is sent.' },
  { file: 'screenshot-settings.png', title: 'Settings', description: 'One page per feature — Profile, General, Floating assistant, Web search, Browser, Files, Terminal, Memory, Obsidian, Privacy, Diagnostics.' },
  { file: 'screenshot-floating.png', title: 'Floating assistant', description: 'A pet and mini chat above your other windows, opened with a global shortcut. Supports Codex-format pets.' },
] as const

export const documentationSections = [
  { title: 'Getting started', description: 'Clone the repo, run scripts/doctor.sh for a read-only environment report, then scripts/setup.sh to create the Python bridge virtualenv and install it. Then cd apps/macos && swift run JarvisOS.', href: '#getting-started' },
  { title: 'Installation', description: 'Requirements: macOS 14+, Xcode 15+ (or a Swift 5.9 toolchain), Python 3.11+. Install a local model yourself (for example ollama pull llama3.2:3b) — ArjunOS never downloads weights on its own.', href: '#installation' },
  { title: 'Build the .app and .dmg', description: 'Run scripts/package.sh to produce dist/ArjunOS.app and dist/ArjunOS-0.1.0.dmg. --open launches it, --install copies it to ~/Applications. Ad-hoc signed for local use, not notarized.', href: '#build' },
  { title: 'Connecting local models', description: 'ArjunOS checks 127.0.0.1:11434 every few seconds, lists installed models, and selects one automatically. Change it from the model menu in the composer.', href: '#local-models' },
  { title: 'Settings', description: 'A left-hand list with one page per feature: Profile, General, Floating assistant, Web search, Browser, Files, Terminal, Memory, Obsidian, Privacy, Diagnostics.', href: '#settings' },
  { title: 'Crew', description: 'Give the boss a job. It splits the work one file per worker, lets workers ask questions and share facts, and lets you pick a memory profile (automatic, boss and several workers, boss sleeps, or one model at a time).', href: '#crew' },
  { title: 'Reading files', description: 'Only paths you type are read. Content is fenced as untrusted data, at most six files per message. Credential stores (SSH keys, keychains, browser logins, private keys) are never read.', href: '#files' },
  { title: 'MCP setup', description: 'One JSON file per MCP server. See docs/mcp.md in the repository.', href: '#mcp' },
  { title: 'Security model', description: 'Loopback only with a per-launch bearer token. One approval per action, expires after 5 minutes. Terminal runs an allow-list. Untrusted pages fence data and switch off tools while open.', href: '#security' },
  { title: 'Troubleshooting', description: 'If the bridge fails to start, the app stays usable and shows the reason in Settings → Diagnostics → Restart. Prefer the packaged .app over swift run.', href: '#troubleshooting' },
] as const
