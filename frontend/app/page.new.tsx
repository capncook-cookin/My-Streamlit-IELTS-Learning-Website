'use client'

import { useEffect, useState } from 'react'
import {
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  Clock3,
  Dices,
  Loader2,
  MessageCircle,
  Search,
  Send,
  Sparkles,
  X,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

// Points at the FastAPI backend (main.py + vocab_routes.py). Override with
// NEXT_PUBLIC_API_URL in .env.local if the API runs somewhere else.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// IELTS Task 2 is officially 250 words minimum, but we warn at 150 because
// that is the lower bound for Task 1 and a sensible "too short" signal for
// Task 2 drafts. The user can still submit below the threshold — this is a
// warning, not a block.
const MIN_WORDS_WARNING = 150

type GradeResult = {
  band_estimate: number
  task_achievement_band: number
  coherence_cohesion_band: number
  lexical_resource_band: number
  grammar_band: number
  task_achievement: string
  coherence_cohesion: string
  lexical_resource: string
  grammar: string
  overall_tip: string
  source: 'ai' | 'heuristic'
}

type VocabResult = {
  term: string
  plain_meaning: string
  context_meaning: string
  part_of_speech: string
  example: string
  synonyms: string[]
}

const prompts = {
  advantages: { label: 'Advantages and disadvantages', text: 'Some people believe that the best way to learn about a country is to study its language and culture. Others believe that it is not necessary. Discuss both views and give your own opinion.' },
  environment: { label: 'Environment and responsibility', text: 'Some people think that environmental problems are too big for individuals to solve. Others believe that individuals can make a difference. Discuss both views and give your own opinion.' },
  technology: { label: 'Technology and learning', text: 'Some people think that technology has made learning easier, while others believe it has made students less focused. Discuss both views and give your own opinion.' },
  work: { label: 'Work and quality of life', text: 'Some people believe that working fewer hours is the best way to improve quality of life. Others think that people should work harder to achieve success. Discuss both views and give your own opinion.' },
  custom: { label: 'Custom topic', text: 'Write your own IELTS Task 2 question here, then use the studio to develop a clear and well-supported response.' },
}
const feedback = [
  'You address both sides of the question and your opinion is clear, but the main ideas could be developed with more specific examples.',
  'Your paragraphs are easy to follow and the ideas progress logically. Use a wider range of linking phrases to make the relationships between ideas more precise.',
  'There is a good range of topic-specific vocabulary. Try to avoid repeating key words by using more natural collocations and paraphrases.',
  'Most sentences are accurate and you attempt some complex structures. Check article use and subject–verb agreement in longer sentences.',
]
const bands = [['Task Achievement', '6.0'], ['Coherence & Cohesion', '6.5'], ['Lexical Resource', '7.0'], ['Grammar', '6.5']]
function countWords(value: string) { return value.trim() ? value.trim().split(/\s+/).length : 0 }

function Header({ view, setView }: { view: 'home' | 'writing' | 'reading'; setView: (view: 'home' | 'writing' | 'reading') => void }) {
  return <header className="forest-appear border-b border-border/80 bg-background/90"><div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8"><button onClick={() => setView('home')} className="flex items-center gap-3 text-left"><div className="ctrllang-logo-crop" aria-label="CtrlLang"><img src="/ctrllang-logo.png" alt="CtrlLang" /></div><div className="hidden border-l border-border pl-3 sm:block"><p className="text-sm font-medium tracking-tight">Language lab</p></div></button><nav className="flex items-center gap-1 rounded-full border border-border bg-card/70 p-1" aria-label="Main navigation"><button onClick={() => setView('home')} className={`nav-pill ${view === 'home' ? 'nav-pill-active' : ''}`}>Home</button><button onClick={() => setView('reading')} className={`nav-pill ${view === 'reading' ? 'nav-pill-active' : ''}`}>Reading</button><button onClick={() => setView('writing')} className={`nav-pill ${view === 'writing' ? 'nav-pill-active' : ''}`}>Writing</button></nav></div></header>
}

function Home({ setView }: { setView: (view: 'home' | 'writing' | 'reading') => void }) {
  return <div className="page-view mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-20"><div className="max-w-3xl forest-appear forest-appear-delay-1"><p className="mb-4 text-sm font-medium uppercase tracking-[0.18em] text-primary">CtrlLang language lab</p><h1 className="max-w-2xl text-balance text-5xl font-semibold leading-[1.05] tracking-tight sm:text-7xl">Read closely. Write clearly.</h1><p className="mt-6 max-w-xl text-lg leading-8 text-muted-foreground">A quiet practice space for ambitious learners. Build the habits behind confident IELTS answers, one focused session at a time.</p><div className="mt-9 flex flex-wrap gap-3"><Button onClick={() => setView('writing')} className="h-12 gap-2 px-6">Start writing <ArrowUpRight className="size-4" /></Button><Button onClick={() => setView('reading')} variant="outline" className="h-12 gap-2 px-6"><BookOpen className="size-4" /> Open a reading</Button></div></div><div className="mt-16 grid gap-5 md:grid-cols-2 forest-appear forest-appear-delay-2"><button onClick={() => setView('writing')} className="feature-card text-left"><span className="feature-number">01</span><h2>Writing studio</h2><p>Practice Task 2 prompts, track your word count, and get notes that point to your next improvement.</p><span className="feature-link">Open studio <ArrowUpRight className="size-4" /></span></button><button onClick={() => setView('reading')} className="feature-card text-left"><span className="feature-number">02</span><h2>Reading room</h2><p>Work through a short academic passage and train your eye for structure, evidence, and meaning.</p><span className="feature-link">Enter reading room <ArrowUpRight className="size-4" /></span></button></div></div>
}

function Reading() {
  return <div className="page-view mx-auto max-w-5xl px-5 py-12 sm:px-8 lg:py-16"><div className="forest-appear forest-appear-delay-1 max-w-2xl"><p className="mb-3 text-sm font-medium uppercase tracking-[0.18em] text-primary">Reading room · passage 01</p><h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">The intelligence of forests</h1><p className="mt-4 text-base leading-7 text-muted-foreground">Read for the central claim, then notice how each paragraph earns its place.</p></div><Card className="forest-appear forest-appear-delay-2 mt-10 border-border/80 shadow-sm"><CardHeader className="border-b border-border/70 px-6 py-5 sm:px-10"><div className="flex items-center justify-between gap-4"><p className="text-sm font-medium uppercase tracking-[0.16em] text-muted-foreground">Academic reading</p><Badge variant="secondary">6 min</Badge></div></CardHeader><CardContent className="px-6 py-8 sm:px-10 sm:py-10"><article className="reading-copy"><p>In a temperate forest, no single tree is truly alone. Beneath the visible floor of leaves and moss, roots meet fungi that carry water and minerals between plants. This hidden network does not make the forest equal; it makes the forest connected.</p><p>Researchers have found that older trees can support younger saplings by sending resources toward the places where shade is deepest. The exchange is practical rather than sentimental. A forest survives because its organisms respond to conditions beyond their individual lives.</p><p>That lesson matters outside the woods. Strong systems are not built from isolated excellence, but from relationships that make knowledge, energy, and care easier to pass along. Reading well begins with the same attention: follow the links, not only the objects.</p></article><div className="mt-10 rounded-lg border border-border bg-secondary/60 p-5"><p className="text-sm font-semibold text-primary">Reader&apos;s note</p><p className="mt-2 text-sm leading-6 text-primary">What is the author&apos;s main comparison in the final paragraph?</p></div></CardContent></Card></div>
}

function Grading({ prompt, essay, onBack, grade }: { prompt: string; essay: Record<string, string>; onBack: () => void; grade: GradeResult | null }) {
  // If we don't have a real grade yet, fall back to the static placeholder so
  // the page still renders cleanly. The "real" path always supplies a grade.
  const fallbackNotes = ['Your response answers the question directly and presents a clear position.', 'The organization is easy to follow; add more specific examples to develop each body paragraph.', 'Your vocabulary is appropriate for the topic. Try a few more precise academic collocations.', 'Review articles and subject–verb agreement when writing longer sentences.']
  const displayBands = grade
    ? [
        ['Task Achievement', grade.task_achievement_band.toFixed(1)],
        ['Coherence', grade.coherence_cohesion_band.toFixed(1)],
        ['Vocabulary', grade.lexical_resource_band.toFixed(1)],
        ['Grammar', grade.grammar_band.toFixed(1)],
      ] as Array<[string, string]>
    : (bands as Array<[string, string]>)
  const overallBand = grade ? grade.band_estimate.toFixed(1) : '6.5'
  const notes = grade
    ? [grade.task_achievement, grade.coherence_cohesion, grade.lexical_resource, grade.grammar]
    : fallbackNotes
  const overallTip = grade?.overall_tip ?? 'Make each paragraph do one clear job: introduce one main idea, explain it, and support it.'
  return <div className="page-view mx-auto max-w-[1500px] px-4 py-8 sm:px-6 lg:py-10"><div className="forest-appear forest-appear-delay-1 mb-6 flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-medium uppercase tracking-[0.18em] text-primary">CtrlLang grading report</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Your writing, reviewed.</h1>{grade && <p className="mt-1 text-xs text-muted-foreground">Source: {grade.source === 'ai' ? 'AI examiner' : 'heuristic placeholder'}</p>}</div><Button variant="outline" onClick={onBack}>Back to writing</Button></div><div className="grading-grid"><Card className="grading-essay forest-appear forest-appear-delay-2"><CardHeader className="border-b border-border/70 px-6 py-5"><div className="flex items-center justify-between"><p className="text-sm font-semibold text-primary">Your response</p><span className="text-sm text-muted-foreground">{countWords(Object.values(essay).join(' '))} words</span></div><p className="mt-4 rounded-lg border border-border bg-secondary/50 p-4 text-sm italic leading-6 text-primary">{prompt}</p></CardHeader><CardContent className="reading-copy px-6 py-8">{Object.entries(essay).filter(([, value]) => value.trim()).map(([key, value]) => <section key={key} className="mb-7"><h2 className="mb-2 text-sm font-semibold capitalize text-primary">{key}</h2><p>{value}</p></section>)}</CardContent></Card><aside className="grading-side forest-appear forest-appear-delay-3"><div className="score-strip"><div className="score-total"><span>Overall band</span><strong>{overallBand}</strong><small>{grade ? (grade.source === 'ai' ? 'AI examiner' : 'Heuristic') : 'Good progress'}</small></div>{displayBands.map(([label, score]) => <div key={label} className="score-card"><span>{label}</span><strong>{score}</strong></div>)}</div><Card className="mt-4 border-border/80"><CardHeader className="border-b border-border/70 px-5 py-4"><p className="text-sm font-semibold">Notes and explanations</p></CardHeader><CardContent className="flex flex-col gap-4 px-5 py-5">{notes.map((note) => <p key={note} className="flex gap-3 text-base leading-7 text-primary"><Check className="mt-1 size-4 shrink-0" />{note}</p>)}<div className="rounded-lg bg-secondary p-4 text-sm leading-6 text-primary"><strong>Overall tip:</strong> {overallTip}</div></CardContent></Card></aside></div></div>
}

function VocabHelper() {
  const [term, setTerm] = useState('')
  const [context, setContext] = useState('')
  const [result, setResult] = useState<VocabResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function lookup() {
    const trimmed = term.trim()
    if (!trimmed) {
      setError('Type a word or phrase to look up.')
      return
    }
    setError(null)
    setResult(null)
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/vocab`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term: trimmed, context }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `Request failed (${res.status})`)
      }
      const data: VocabResult = await res.json()
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Lookup failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <CardContent className="flex min-h-[320px] flex-col gap-4 px-5 py-6">
      <div className="flex flex-col gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-primary" htmlFor="vocab-term">Word or phrase</label>
        <div className="flex items-center gap-2 rounded-lg border border-input bg-card px-3 py-2 focus-within:ring-2 focus-within:ring-ring">
          <Search className="size-4 text-muted-foreground" />
          <input
            id="vocab-term"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') lookup() }}
            placeholder="e.g. paraphrase"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            aria-label="Vocabulary term"
          />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-primary" htmlFor="vocab-context">Used in this essay sentence <span className="font-normal normal-case text-muted-foreground">(optional - gives a context meaning)</span></label>
        <Textarea
          id="vocab-context"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="e.g. The introduction should paraphrase the question in your own words."
          className="min-h-20 resize-y bg-card text-sm"
        />
      </div>
      <Button onClick={lookup} disabled={loading} className="self-start gap-2">
        {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
        {loading ? 'Looking up…' : 'Look up'}
      </Button>
      {error && <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
      {result && !error && (
        <div className="rounded-lg border border-border bg-secondary/60 p-4 text-sm leading-6 text-primary">
          <p className="font-semibold capitalize">{result.term} <span className="font-normal italic text-muted-foreground">- {result.part_of_speech}</span></p>
          <div className="mt-3 space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Plain meaning</p>
              <p className="mt-1">{result.plain_meaning}</p>
            </div>
            {result.context_meaning && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">In your essay context</p>
                <p className="mt-1">{result.context_meaning}</p>
              </div>
            )}
            {result.example && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Example</p>
                <p className="mt-1 italic">{result.example}</p>
              </div>
            )}
            {result.synonyms?.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Synonyms</p>
                <p className="mt-1">{result.synonyms.join(', ')}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </CardContent>
  )
}

function WritingWorkspace({ onGrade }: { onGrade: (prompt: string, essay: Record<string, string>, grade: GradeResult) => void }) {
  const [stage, setStage] = useState<'topics' | 'write'>('topics')
  const [customTopic, setCustomTopic] = useState('')
  const [prompt, setPrompt] = useState<keyof typeof prompts>('advantages')
  const [isShuffling, setIsShuffling] = useState(false)
  const [essay, setEssay] = useState({ introduction: '', body1: '', body2: '', conclusion: '' })
  const [gradeError, setGradeError] = useState<string | null>(null)
  const [isGrading, setIsGrading] = useState(false)
  const randomizePrompt = () => {
    if (isShuffling) return
    const options = (Object.keys(prompts).filter((option) => option !== 'custom') as Array<keyof typeof prompts>)
    const next = options.filter((option) => option !== prompt)[Math.floor(Math.random() * Math.max(1, options.length - 1))] ?? options[0]
    setIsShuffling(true)
    window.setTimeout(() => { setPrompt(next); setIsShuffling(false) }, 850)
  }
  const [showSample, setShowSample] = useState(false)
  // Live writing clock. Restored in v3 — the new tree referenced elapsedSeconds
  // but never incremented it, so the counter was stuck at 00:00.
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const elapsedTime = `${String(Math.floor(elapsedSeconds / 60)).padStart(2, '0')}:${String(elapsedSeconds % 60).padStart(2, '0')}`
  const wordCount = countWords(Object.values(essay).join(' '))
  const update = (key: keyof typeof essay, value: string) => setEssay((current) => ({ ...current, [key]: value }))
  const fields = [['introduction', 'Introduction'], ['body1', 'Body 1'], ['body2', 'Body 2'], ['conclusion', 'Conclusion']] as const
  const activePrompt = prompt === 'custom' && customTopic.trim() ? customTopic.trim() : prompts[prompt].text

  // 150-word warning: shown when the student has written something but it's
  // still under the recommended minimum. Submit stays enabled (per user
  // choice — this is a warning, not a block).
  const showWordWarning = wordCount > 0 && wordCount < MIN_WORDS_WARNING

  async function submitForGrading() {
    setIsGrading(true)
    setGradeError(null)
    try {
      const res = await fetch(`${API_URL}/api/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: activePrompt, essay: Object.values(essay).join('\n\n') }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail ?? `Request failed (${res.status})`)
      }
      const data: GradeResult = await res.json()
      onGrade(activePrompt, essay, data)
    } catch (e) {
      setGradeError(e instanceof Error ? e.message : 'Grading failed.')
    } finally {
      setIsGrading(false)
    }
  }

  if (stage === 'topics') return <div className="page-view mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14"><div className="forest-appear forest-appear-delay-1 flex flex-wrap items-end justify-between gap-5"><div><p className="text-sm font-medium uppercase tracking-[0.18em] text-primary">Writing library</p><h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">Choose a topic.</h1><p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">Pick a Task 2 question to begin, or bring your own idea into the studio.</p></div><div className="flex items-center gap-2"><Button variant="outline" size="sm" onClick={randomizePrompt} disabled={isShuffling}><Dices data-icon="inline-start" /> {isShuffling ? 'Shuffling…' : 'Random topic'}</Button><span className="hidden rounded-full border border-border bg-secondary px-3 py-1.5 text-sm text-primary sm:inline-flex">Task 2 topic library</span></div></div><div className={`topic-grid mt-10 forest-appear forest-appear-delay-2 ${isShuffling ? 'topic-grid-shuffling' : ''}`} aria-live="polite">{Object.entries(prompts).filter(([key]) => key !== 'custom').map(([key, item]) => <button key={key} onClick={() => { setPrompt(key as keyof typeof prompts); setStage('write') }} className="topic-card text-left"><div className="topic-card-media"><img src="/ielts-task-example.png" alt="Example topic visual" /><span>Discussion</span></div><span className="feature-number">TASK 2</span><h2>{item.label}</h2><p>{item.text}</p><span className="feature-link">Start practice <ArrowUpRight className="size-4" /></span></button>)}<div className="topic-card topic-card-custom"><span className="feature-number">YOUR IDEA</span><h2>Custom topic</h2><p>Write or paste your own IELTS Task 2 question, then enter the studio.</p><textarea value={customTopic} onChange={(event) => setCustomTopic(event.target.value)} placeholder="Type your topic here..." className="mt-4 min-h-24 w-full resize-y rounded-lg border border-border bg-card px-3 py-2 text-sm leading-6 text-primary outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring" aria-label="Custom topic" /><Button onClick={() => { if (customTopic.trim()) { setPrompt('custom'); setStage('write') } }} disabled={!customTopic.trim()} className="mt-4 gap-2">Use this topic <ArrowUpRight className="size-4" /></Button></div></div></div>
  return <div className="page-view mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-8"><div className="mb-6 forest-appear forest-appear-delay-1"><p className="text-sm font-medium uppercase tracking-[0.18em] text-primary">CtrlLang writing studio</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Make your argument count.</h1></div><div className="writing-grid"><Card className="writing-pane forest-appear forest-appear-delay-1"><CardHeader className="border-b border-border/70 px-5 py-4"><p className="text-sm font-semibold">Writing Task 2</p><p className="mt-2 text-sm italic leading-6 text-primary">{activePrompt}</p><div className="prompt-image-placeholder"><span>Topic image placeholder</span></div></CardHeader><CardContent className="flex flex-col gap-6 px-5 py-6"><div><p className="text-sm font-semibold text-primary">Writing focus</p><p className="mt-2 text-sm leading-6 text-muted-foreground">Paraphrase the question, state your position, then build each paragraph around one clear idea.</p></div><div className="writing-hints"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Writing hints</p><ul className="mt-3 flex flex-col gap-2 text-sm leading-6 text-primary"><li>• Make your opinion clear in the introduction.</li><li>• Support each body paragraph with a specific example.</li><li>• End by restating your position without adding a new idea.</li></ul></div></CardContent></Card><Card className="writing-pane forest-appear forest-appear-delay-2"><CardHeader className="flex-row items-center justify-between border-b border-border/70 px-5 py-4"><div className="flex items-center gap-3"><p className="text-sm font-semibold">Your answer</p></div><div className="flex items-center gap-3"><div className="writing-clock" aria-label={`Time spent writing ${elapsedTime}`}><Clock3 className="size-4" /><span>{elapsedTime}</span></div><span className="text-sm text-primary">Word count: {wordCount}</span><button type="button" onClick={() => setShowSample(!showSample)} className={`sample-toggle ${showSample ? 'sample-toggle-on' : ''}`} aria-pressed={showSample}><span />Sample</button></div></CardHeader><CardContent className="flex flex-col gap-5 overflow-y-auto px-5 py-6">{showSample && <div className="sample-page"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Sample page</p><img src="/ielts-task-example.png" alt="Example IELTS task diagram" className="mt-3 w-full rounded-md border border-border/70" /><p className="mt-3 text-sm leading-7 text-primary">Learning a country&apos;s language and culture offers a deeper understanding of its people and traditions. Although travel provides valuable first-hand experience, structured study creates a stronger foundation for meaningful communication.</p></div>}{fields.map(([key, label]) => <label key={key} className="flex flex-col gap-2 text-sm font-semibold text-primary">{label}<Textarea value={essay[key]} onChange={(event) => update(key, event.target.value)} placeholder="Write your response here..." className={`writing-field ${key === 'overview' ? 'min-h-24' : 'min-h-32'} resize-y bg-card`} /></label>)}<div className="flex flex-col gap-2"><Button className="self-start" disabled={!wordCount || isGrading} onClick={submitForGrading}>{isGrading ? <><Loader2 className="size-4 animate-spin" /> Grading…</> : <>Grade my essay <ArrowUpRight className="size-4" /></>}</Button>{showWordWarning && <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800" role="status">You have {wordCount} word{wordCount === 1 ? '' : 's'} — IELTS recommends at least {MIN_WORDS_WARNING}. You can still submit, but a longer response is usually scored higher.</p>}{gradeError && <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">{gradeError}</p>}</div></CardContent></Card><Card className="writing-pane forest-appear forest-appear-delay-3"><CardHeader className="border-b border-border/70 px-5 py-4"><div className="flex items-center gap-2"><Sparkles className="size-4 text-primary" /><p className="text-sm font-semibold">Vocabulary helper</p><span className="size-2 rounded-full bg-accent" /></div></CardHeader><VocabHelper /></Card></div></div></div>
}

function Writing() {
  const [prompt, setPrompt] = useState<keyof typeof prompts>('advantages')
  const [essay, setEssay] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [hasFeedback, setHasFeedback] = useState(false)
  const words = countWords(essay)
  function getFeedback() { setIsLoading(true); window.setTimeout(() => { setIsLoading(false); setHasFeedback(true) }, 900) }
  return <div className="page-view mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14"><div className="forest-appear forest-appear-delay-1 mb-10 max-w-2xl"><p className="mb-3 text-sm font-medium uppercase tracking-[0.18em] text-primary">CtrlLang writing studio</p><h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">Make your argument count.</h1><p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">Practice with an IELTS Task 2 prompt, then get focused feedback that helps you write with more clarity and confidence.</p></div><div className="grid gap-6 lg:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)]"><section aria-labelledby="prompt-heading" className="forest-appear forest-appear-delay-2 flex min-w-0 flex-col gap-6"><Card className="border-border/80 shadow-sm"><CardHeader className="gap-4 border-b border-border/70 px-6 py-5 sm:px-8"><div className="flex items-center justify-between gap-4"><div><p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Choose a prompt</p><h2 id="prompt-heading" className="mt-1 text-2xl">Your question</h2></div><span className="text-xs text-muted-foreground">1 of 2</span></div><Select value={prompt} onValueChange={(value) => setPrompt(value as keyof typeof prompts)}><SelectTrigger className="h-11 w-full bg-secondary/40"><SelectValue /></SelectTrigger><SelectContent>{Object.entries(prompts).map(([key, item]) => <SelectItem key={key} value={key}>{item.label}</SelectItem>)}</SelectContent></Select></CardHeader><CardContent className="px-6 py-7 sm:px-8 sm:py-8"><blockquote className="border-l-2 border-primary pl-5 text-lg leading-8 text-foreground/90">{prompts[prompt].text}</blockquote><p className="mt-6 text-sm leading-6 text-muted-foreground">Write at least 250 words. Aim for a clear position, well-developed ideas, and a range of grammatical structures.</p></CardContent></Card><Card className="border-border/80 shadow-sm"><CardHeader className="flex-row items-center justify-between gap-4 px-6 py-5 sm:px-8"><div><p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Your response</p><h2 className="mt-1 text-2xl">Build your essay</h2></div><span className="text-sm tabular-nums text-muted-foreground">{words} words <span className="text-border">/</span> 250 min</span></CardHeader><CardContent className="px-6 pb-6 sm:px-8 sm:pb-8"><Textarea aria-label="Your IELTS essay" value={essay} onChange={(event) => setEssay(event.target.value)} placeholder="Start writing your introduction..." className="min-h-[330px] resize-y border-border/80 bg-secondary/25 p-4 text-base leading-7 shadow-none focus-visible:ring-primary/30" /><div className="mt-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><p className="text-xs leading-5 text-muted-foreground">Your draft stays private in this practice session.</p><Button onClick={getFeedback} disabled={isLoading} className="h-11 gap-2 px-5">{isLoading ? 'Reviewing…' : 'Get feedback'} <ArrowUpRight className="size-4" /></Button></div></CardContent></Card></section><aside aria-labelledby="feedback-heading" className="forest-appear forest-appear-delay-3 w-full lg:max-w-md lg:justify-self-end"><Card className="border-border/80 bg-card shadow-sm"><CardHeader className="border-b border-border/70 px-6 py-5 sm:px-7"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Your review</p><h2 id="feedback-heading" className="mt-1 text-3xl">Feedback</h2></div>{hasFeedback && <Badge className="rounded-full border-border bg-secondary text-primary">Complete</Badge>}</div></CardHeader><CardContent className="px-6 py-7 sm:px-8 sm:py-8">{!hasFeedback ? <div className="flex min-h-[220px] flex-col items-center justify-center text-center"><div className="mb-5 flex size-14 items-center justify-center rounded-full border border-border bg-secondary"><ChevronDown className="size-5 text-muted-foreground" /></div><h3 className="text-2xl">Your notes will appear here</h3><p className="mt-3 max-w-xs text-sm leading-6 text-muted-foreground">Write your essay and select “Get feedback” when you are ready.</p></div> : <div className="feedback-reveal flex flex-col gap-5"><div className="flex items-end justify-between border-b border-border/70 pb-6"><div><p className="text-sm text-muted-foreground">Estimated overall band</p><p className="mt-1 text-6xl leading-none">6.5</p></div><span className="pb-1 text-sm text-muted-foreground">Good work</span></div><div className="grid grid-cols-2 gap-3">{bands.map(([label, score]) => <div key={label} className="rounded-lg border border-border/70 bg-secondary p-3"><p className="min-h-9 text-xs leading-4 text-muted-foreground">{label}</p><p className="mt-2 text-2xl">{score}</p></div>)}</div><div className="flex flex-col gap-4">{feedback.map((item) => <p key={item} className="flex gap-3 text-base leading-7 text-primary"><Check className="mt-1 size-4 shrink-0 text-primary" />{item}</p>)}</div><div className="rounded-lg border border-border bg-secondary p-4 text-sm leading-6 text-primary"><Sparkles className="mr-2 inline size-4" />Overall tip: Make each body paragraph do one clear job: introduce one main idea, explain it, and support it with a specific example.</div></div>}</CardContent></Card></aside></div></div>
}

export default function Page() {
  const [view, setView] = useState<'home' | 'writing' | 'reading'>('home')
  const [chatOpen, setChatOpen] = useState(false)
  // Stash the most recent grade so the Grading view can render the real
  // numbers (not the static placeholders) when the user reaches it.
  const [latestGrade, setLatestGrade] = useState<{ prompt: string; essay: Record<string, string>; grade: GradeResult } | null>(null)
  return <main className="min-h-screen bg-background text-foreground forest-texture"><Header view={view} setView={setView} />{view === 'home' && <Home setView={setView} />}{view === 'reading' && <Reading />}{view === 'writing' && <WritingWorkspace onGrade={(prompt, essay, grade) => { setLatestGrade({ prompt, essay, grade }); setView('reading') }} />}{latestGrade && view === 'reading' && latestGrade && <Grading prompt={latestGrade.prompt} essay={latestGrade.essay} grade={latestGrade.grade} onBack={() => { setLatestGrade(null); setView('writing') }} />}<div className={`chat-widget ${chatOpen ? 'chat-widget-open' : ''}`}>{chatOpen && <div className="chat-panel"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div><p className="text-sm font-semibold">CtrlLang guide</p><p className="text-xs text-muted-foreground">Ask about your practice</p></div><button onClick={() => setChatOpen(false)} aria-label="Close chat"><X className="size-4" /></button></div><div className="flex min-h-24 flex-col justify-end gap-2 p-4"><p className="rounded-lg bg-secondary px-3 py-2 text-sm leading-5 text-primary">Need a starting point? Try reading the prompt aloud before you write.</p></div><div className="flex gap-2 border-t border-border p-3"><input aria-label="Chat message" placeholder="Ask CtrlLang..." className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none" /><Button size="icon" aria-label="Send message"><Send className="size-4" /></Button></div></div>}<button className="chat-bubble" onClick={() => setChatOpen(!chatOpen)} aria-label={chatOpen ? 'Close chat' : 'Open chat'}>{chatOpen ? <X className="size-5" /> : <MessageCircle className="size-5" />}</button></div></main>
}
