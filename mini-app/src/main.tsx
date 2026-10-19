import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, NavLink, Route, Routes, useParams } from 'react-router-dom'
import { authenticate, getCharacter, getCharacters, type AuthSession, type Character } from './api'
import './style.css'

type SessionState = { session: AuthSession | null; error: string | null; loading: boolean }
const SessionContext = createContext<SessionState>({ session: null, error: null, loading: true })
const useSession = () => useContext(SessionContext)

function useTelegramTheme() {
  useEffect(() => {
    const webApp = window.Telegram?.WebApp
    if (!webApp) return
    const applyTheme = () => {
      document.documentElement.dataset.theme = webApp.colorScheme
      const variables: Record<string, string> = {
        '--tg-bg': webApp.themeParams.bg_color,
        '--tg-text': webApp.themeParams.text_color,
        '--tg-hint': webApp.themeParams.hint_color,
        '--tg-button': webApp.themeParams.button_color,
        '--tg-button-text': webApp.themeParams.button_text_color,
      }
      for (const [name, value] of Object.entries(variables)) {
        if (value) document.documentElement.style.setProperty(name, value)
      }
    }
    webApp.ready()
    webApp.expand()
    applyTheme()
    webApp.onEvent('themeChanged', applyTheme)
    return () => webApp.offEvent('themeChanged', applyTheme)
  }, [])
}

function SessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>({ session: null, error: null, loading: true })
  useEffect(() => {
    const initData = window.Telegram?.WebApp?.initData
    if (!initData) {
      setState({ session: null, error: 'Open this app from the Telegram bot to sign in.', loading: false })
      return
    }
    authenticate(initData).then(session => setState({ session, error: null, loading: false }))
      .catch(error => setState({ session: null, error: error.message, loading: false }))
  }, [])
  const value = useMemo(() => state, [state])
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

function Status({ text, error = false }: { text: string; error?: boolean }) {
  return <p className={error ? 'status status-error' : 'status'} role={error ? 'alert' : 'status'}>{text}</p>
}

function Shell() {
  useTelegramTheme()
  const { loading, error, session } = useSession()
  if (loading) return <main className="center-screen"><Status text="Verifying your Telegram session…" /></main>
  if (error || !session) return <main className="center-screen"><Brand /><Status text={error ?? 'Sign-in required'} error /></main>
  return <div className="app-shell">
    <header className="topbar"><Link className="brand" to="/">✦ <span>Adventurer’s Ledger</span></Link><span className="user-chip">{session.user.username}</span></header>
    <nav className="navigation" aria-label="Main navigation">
      <NavLink to="/" end>Home</NavLink><NavLink to="/characters">Characters</NavLink><NavLink to="/settings">Settings</NavLink>
    </nav>
    <main className="page"><Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/characters" element={<Characters />} />
      <Route path="/characters/:id" element={<CharacterDetails />} />
      <Route path="/create" element={<ComingSoon title="Create character" />} />
      <Route path="/backstory" element={<ComingSoon title="AI backstory" />} />
      <Route path="/settings" element={<ComingSoon title="Settings" />} />
      <Route path="*" element={<Status text="That page does not exist." error />} />
    </Routes></main>
  </div>
}

function Brand() { return <div className="brand brand-large">✦ <span>Adventurer’s Ledger</span></div> }

function Dashboard() {
  const { session } = useSession()
  const [count, setCount] = useState<number | null>(null)
  useEffect(() => { if (session) getCharacters(session.access).then(chars => setCount(chars.length)).catch(() => setCount(null)) }, [session])
  return <>
    <section className="hero"><div className="hero-mark">✧</div><div><p className="kicker">Your campaign, in one place</p><h1>Welcome back,<br />{session?.user.username}</h1><p className="hero-copy">Keep your adventurers ready for the next session.</p></div></section>
    <section className="dashboard-grid" aria-label="Quick actions">
      <Link className="action action-primary" to="/characters"><span className="action-icon">♙</span><span><strong>My characters</strong><small>{count === null ? 'View your roster' : `${count} ${count === 1 ? 'character' : 'characters'}`}</small></span><span className="arrow">›</span></Link>
      <Link className="action" to="/create"><span className="action-icon">＋</span><span><strong>Create character</strong><small>Build a new adventurer</small></span><span className="arrow">›</span></Link>
      <Link className="action" to="/backstory"><span className="action-icon">✧</span><span><strong>AI backstory</strong><small>Shape a character’s past</small></span><span className="arrow">›</span></Link>
      <Link className="action" to="/settings"><span className="action-icon">⚙</span><span><strong>Settings</strong><small>Manage your preferences</small></span><span className="arrow">›</span></Link>
    </section>
  </>
}

function Characters() {
  const { session } = useSession()
  const [characters, setCharacters] = useState<Character[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { if (session) getCharacters(session.access).then(setCharacters).catch(reason => setError(reason.message)) }, [session])
  return <section><PageHeading title="My characters" subtitle="Your adventurers, ready for the road." />
    {error && <Status text={error} error />}
    {!error && characters === null && <Status text="Loading your characters…" />}
    {!error && characters?.length === 0 && <div className="empty"><span>♙</span><h2>No characters yet</h2><p>Your roster is waiting for its first adventurer.</p><Link className="button" to="/create">Create character</Link></div>}
    <div className="character-list">{characters?.map(character => <Link className="character-row" to={`/characters/${character.id}`} key={character.id}>
      <span className="portrait">{character.name?.[0]?.toUpperCase() ?? '✦'}</span><span className="character-name"><strong>{character.name || 'Unnamed adventurer'}</strong><small>{character.kind} · {character.spec_class}</small></span><span className="level">Lv. {character.level ?? 1}</span><span className="arrow">›</span>
    </Link>)}</div>
  </section>
}

function CharacterDetails() {
  const { id = '' } = useParams()
  const { session } = useSession()
  const [character, setCharacter] = useState<Character | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { if (session) getCharacter(session.access, id).then(setCharacter).catch(reason => setError(reason.message)) }, [id, session])
  if (error) return <Status text={error} error />
  if (!character) return <Status text="Loading character…" />
  return <section><Link className="back-link" to="/characters">‹ My characters</Link><PageHeading title={character.name || 'Unnamed adventurer'} subtitle={`${character.kind} ${character.spec_class}`} />
    <dl className="details"><div><dt>Level</dt><dd>{character.level ?? 1}</dd></div><div><dt>Alignment</dt><dd>{character.alignment || 'Not set'}</dd></div><div><dt>Background</dt><dd>{character.background || 'Not set'}</dd></div></dl>
    <Status text="Editing and additional character sections are not available yet." />
  </section>
}

function PageHeading({ title, subtitle }: { title: string; subtitle: string }) { return <header className="page-heading"><h1>{title}</h1><p>{subtitle}</p></header> }

function ComingSoon({ title }: { title: string }) { return <section><PageHeading title={title} subtitle="This section is not available yet." /><Status text="Your existing character data remains unchanged." /><Link className="back-link" to="/">‹ Back to dashboard</Link></section> }

createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><SessionProvider><Shell /></SessionProvider></BrowserRouter></React.StrictMode>)
