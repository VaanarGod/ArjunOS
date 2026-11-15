export const APP_NAME = 'ArjunOS'
export const APP_VERSION = '0.1.0'
export const APP_STATUS = 'Early build'
export const MIN_MACOS = 'macOS 14 (Sonoma) or later'
export const LICENSE = 'Apache-2.0'

export const REPO_URL = 'https://github.com/VaanarGod/ArjunOS'
export const API_URL = 'https://api.github.com/repos/VaanarGod/ArjunOS'
export const RELEASES_URL = `${REPO_URL}/releases`
export const DOCS_URL = `${REPO_URL}/tree/main/docs`
export const LICENSE_URL = `${REPO_URL}/blob/main/LICENSE`
export const DOWNLOAD_URL = `${REPO_URL}/releases/latest/download/ArjunOS-0.1.0.dmg`

export const techStack = [
  { label: 'macOS 14+', value: 'Native SwiftUI app' },
  { label: 'Swift 5.9', value: 'JarvisCore · JarvisOS' },
  { label: 'Python 3.11+', value: 'FastAPI bridge' },
  { label: 'Apache-2.0', value: 'Open source' },
] as const

export const features = [
  { id: 'local-chat', title: 'Local chat', description: 'Streams from models you already run: Ollama, LM Studio, llama.cpp, vLLM, or any OpenAI-compatible server. Models are discovered automatically and a default is chosen for you.', status: 'Implemented', icon: 'MessageSquare' },
  { id: 'crew', title: 'Crew', description: 'A boss model splits a job between small worker models, each with its own browser panel. Free RAM decides who is awake.', status: 'Implemented', icon: 'Users' },
  { id: 'browser', title: 'Built-in browser', description: 'Tabs, downloads, popups, camera/mic prompts. Ask about the page you have open; it is read as the primary source.', status: 'Implemented', icon: 'Globe' },
  { id: 'web-search', title: 'Web search', description: 'DuckDuckGo, no key required. Asks permission first; only a short query is ever sent.', status: 'Implemented', icon: 'Search' },
  { id: 'memory', title: 'Memory', description: 'Say "remember …". Notes live in local SQLite (FTS5), are all listed when you open the screen, can be undone, and never store secrets.', status: 'Implemented', icon: 'Database' },
  { id: 'profile', title: 'Profile', description: 'Tell it what to call you, set how you like answers, and write your own standing instructions.', status: 'Implemented', icon: 'UserRound' },
  { id: 'mcp', title: 'MCP tools', description: 'Connect Model Context Protocol servers with one JSON file per server.', status: 'Implemented', icon: 'Plug' },
  { id: 'files', title: 'Any file', description: 'Attach a file, or just write its path in a message. Reads PDF, Word, Excel, PowerPoint, SQLite, archives, images.', status: 'Implemented', icon: 'FileText' },
  { id: 'obsidian', title: 'Obsidian', description: 'Connect a vault so the model can search it and add notes to its own folder.', status: 'Implemented', icon: 'BookOpen' },
  { id: 'floating', title: 'Floating assistant', description: 'A pet and mini chat above your other windows, opened with a global shortcut.', status: 'Implemented', icon: 'Sparkles' },
  { id: 'terminal', title: 'Sandboxed terminal', description: 'A short allow-list of commands, each run only after you approve it.', status: 'Implemented', icon: 'Terminal' },
  { id: 'create-files', title: 'Create files', description: 'Ask it to write a file and it does so in the workspace folder, never overwriting.', status: 'Implemented', icon: 'FolderPlus' },
  { id: 'rich-answers', title: 'Rich answers', description: 'Markdown, tables, code with Copy, and math (KaTeX), all rendered offline.', status: 'Implemented', icon: 'Palette' },
  { id: 'security', title: 'Local-first security', description: 'Loopback only, per-launch bearer token, one approval per action.', status: 'Design principle', icon: 'Shield' },
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
  { title: 'Getting started', description: 'Clone the repo, run scripts/setup.sh, then swift run JarvisOS.', href: '#getting-started' },
  { title: 'Installation', description: 'Requirements: macOS 14+, Xcode 15+, Python 3.11+.', href: '#installation' },
  { title: 'Build the .app and .dmg', description: 'Run scripts/package.sh to produce dist/ArjunOS.app.', href: '#build' },
  { title: 'Connecting local models', description: 'ArjunOS checks 127.0.0.1:11434 every few seconds.', href: '#local-models' },
  { title: 'Security model', description: 'Loopback only with a per-launch bearer token.', href: '#security' },
] as const

export const integrations = [
  { id: 'ollama', name: 'Ollama', category: 'Local Inference', status: 'Implemented', desc: 'Streams from local Ollama models automatically.', icon: 'Cpu' },
  { id: 'llamacpp', name: 'llama.cpp', category: 'Local Inference', status: 'Implemented', desc: 'Supports direct connections to llama.cpp servers.', icon: 'Terminal' },
  { id: 'lmstudio', name: 'LM Studio', category: 'Local Inference', status: 'Implemented', desc: 'Connects to LM Studio local server.', icon: 'Monitor' },
  { id: 'vllm', name: 'vLLM', category: 'Local Inference', status: 'Implemented', desc: 'High-throughput local model serving.', icon: 'Zap' },
  { id: 'openai', name: 'OpenAI', category: 'Cloud AI', status: 'Implemented', desc: 'Support for OpenAI-compatible APIs (optional).', icon: 'Cloud' },
  { id: 'mcp', name: 'MCP', category: 'Tools', status: 'Implemented', desc: 'Model Context Protocol servers via JSON.', icon: 'Plug' },
  { id: 'browser', name: 'Playwright', category: 'Tools', status: 'Planned', desc: 'Advanced browser automation for agents.', icon: 'Globe' },
  { id: 'whisper', name: 'Whisper', category: 'Speech', status: 'Planned', desc: 'Local speech-to-text integration.', icon: 'Mic' },
  { id: 'piper', name: 'Piper', category: 'Speech', status: 'Planned', desc: 'Fast local speech synthesis.', icon: 'Volume2' },
  { id: 'obsidian', name: 'Obsidian', category: 'Automation', status: 'Implemented', desc: 'Search vaults and write to a specific folder.', icon: 'BookOpen' },
  { id: 'gh', name: 'GitHub', category: 'Automation', status: 'Planned', desc: 'Read repos and issues directly from chat.', icon: 'Github' },
  { id: 'homekit', name: 'Home Assistant', category: 'Automation', status: 'Planned', desc: 'Control smart home devices locally.', icon: 'Home' },
] as const
