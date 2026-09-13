'use client'

import { useState } from 'react'
import { ArrowUpRight, BookOpen, Check, ChevronDown, Clock3, Dices, MessageCircle, Search, Send, Sparkles, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

// Points at the FastAPI backend (main.py). Override with NEXT_PUBLIC_API_URL
// in .env.local if it's running somewhere other than localhost:8000.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

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

type DictionaryEntry = {
  term: string
  plain_meaning: string
  context_meaning: string
  part_of_speech: string
  example: string
  synonyms: string[]
  collocations: { phrase: string; example: string }[]
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
  return <header className="forest-appear border-b border-border/80 bg-background/90"><div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8"><button onClick={() => setView('home')} className="flex items-center gap-3 text-left"><div className="ctrllang-logo-crop" aria-label="CtrlLang"><img src="/ctrllang-logo.png" alt="CtrlLang" /></div><div className="hidden border-l border-border pl-3 sm:block"><p className="text-sm font-medium tracking-tight">Language lab</p></div></button><nav className="flex items-center gap-1 rounded-full border border-border bg-card/70 p-1" aria-label="Main navigation"><button onClick={() => setView('home')} className={`nav-pill ${view === 'home' ? 'nav-pill-active' : ''}`}>Home</button><button onClick={() => setView('reading')} className={`nav-pill ${view === 'reading' ? 'nav-pill-active' : ''}`}>Reading</button><button onClick={() => setView('writing')} className={`nav-pill ${view === 'writing' ? 'nav-pill-active' : ''}`}>Writing</button></nav><Badge variant="outline" className="hidden gap-2 rounded-full px-3 py-1.5 font-normal text-muted-foreground md:flex"><Clock3 className="size-3.5" aria-hidden="true" />Task 2 · 40 min</Badge></div></header>
}

function Home({ setView }: { setView: (view: 'home' | 'writing' | 'reading') => void }) {
  return <div className="page-view mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-20"><div className="max-w-3xl forest-appear forest-appear-delay-1"><p className="mb-4 text-sm font-medium uppercase tracking-[0.18em] text-primary">CtrlLang language lab</p><h1 className="max-w-2xl text-balance text-5xl font-semibold leading-[1.05] tracking-tight sm:text-7xl">Read closely. Write clearly.</h1><p className="mt-6 max-w-xl text-lg leading-8 text-muted-foreground">A quiet practice space for ambitious learners. Build the habits behind confident IELTS answers, one focused session at a time.</p><div className="mt-9 flex flex-wrap gap-3"><Button onClick={() => setView('writing')} className="h-12 gap-2 px-6">Start writing <ArrowUpRight className="size-4" /></Button><Button onClick={() => setView('reading')} variant="outline" className="h-12 gap-2 px-6"><BookOpen className="size-4" /> Open a reading</Button></div></div><div className="mt-16 grid gap-5 md:grid-cols-2 forest-appear forest-appear-delay-2"><button onClick={() => setView('writing')} className="feature-card text-left"><span className="feature-number">01</span><h2>Writing studio</h2><p>Practice Task 2 prompts, track your word count, and get notes that point to your next improvement.</p><span className="feature-link">Open studio <ArrowUpRight className="size-4" /></span></button><button onClick={() => setView('reading')} className="feature-card text-left"><span className="feature-number">02</span><h2>Reading room</h2><p>Work through a short academic passage and train your eye for structure, evidence, and meaning.</p><span className="feature-link">Enter reading room <ArrowUpRight className="size-4" /></span></button></div></div>
}

function Reading() {
  return <div className="page-view mx-auto max-w-5xl px-5 py-12 sm:px-8 lg:py-16"><div className="forest-appear forest-appear-delay-1 max-w-2xl"><p className="mb-3 text-sm font-medium uppercase tracking-[0.18em] text-primary">Reading room · passage 01</p><h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">The intelligence of forests</h1><p className="mt-4 text-base leading-7 text-muted-foreground">Read for the central claim, then notice how each paragraph earns its place.</p></div><Card className="forest-appear forest-appear-delay-2 mt-10 border-border/80 shadow-sm"><CardHeader className="border-b border-border/70 px-6 py-5 sm:px-10"><div className="flex items-center justify-between gap-4"><p className="text-sm font-medium uppercase tracking-[0.16em] text-muted-foreground">Academic reading</p><Badge variant="secondary">6 min</Badge></div></CardHeader><CardContent className="px-6 py-8 sm:px-10 sm:py-10"><article className="reading-copy"><p>In a temperate forest, no single tree is truly alone. Beneath the visible floor of leaves and moss, roots meet fungi that carry water and minerals between plants. This hidden network does not make the forest equal; it makes the forest connected.</p><p>Researchers have found that older trees can support younger saplings by sending resources toward the places where shade is deepest. The exchange is practical rather than sentimental. A forest survives because its organisms respond to conditions beyond their individual lives.</p><p>That lesson matters outside the woods. Strong systems are not built from isolated excellence, but from relationships that make knowledge, energy, and care easier to pass along. Reading well begins with the same attention: follow the links, not only the objects.</p></article><div className="mt-10 rounded-lg border border-border bg-secondary/60 p-5"><p className="text-sm font-semibold text-primary">Reader&apos;s note</p><p className="mt-2 text-sm leading-6 text-primary">What is the author&apos;s main comparison in the final paragraph?</p></div></CardContent></Card></div>
}

function WritingWorkspace() {
  const [stage, setStage] = useState<'topics' | 'write'>('topics')
  const [customTopic, setCustomTopic] = useState('')
  const [prompt, setPrompt] = useState<keyof typeof prompts>('advantages')
  const [essay, setEssay] = useState({ introduction: '', body1: '', body2: '', conclusion: '' })
  const randomizePrompt = () => {
    const options = Object.keys(prompts) as Array<keyof typeof prompts>
    const choices = options.filter((option) => option !== prompt)
    setPrompt(choices[Math.floor(Math.random() * choices.length)] ?? options[0])
  }
  const [showSample, setShowSample] = useState(false)
  const wordCount = countWords(Object.values(essay).join(' '))
  const update = (key: keyof typeof essay, value: string) => setEssay((current) => ({ ...current, [key]: value }))
  const fields = [['introduction', 'Introduction'], ['body1', 'Body 1'], ['body2', 'Body 2'], ['conclusion', 'Conclusion']] as const
  const activePrompt = prompt === 'custom' && customTopic.trim() ? customTopic.trim() : prompts[prompt].text

  // Grading
  const [isGrading, setIsGrading] = useState(false)
  const [gradeResult, setGradeResult] = useState<GradeResult | null>(null)
  const [gradeError, setGradeError] = useState<string | null>(null)
  async function getFeedback() {
    setIsGrading(true)
    setGradeError(null)
    const fullEssay = fields.map(([key, label]) => `${label}:\n${essay[key]}`).join('\n\n')
    try {
      const res = await fetch(`${API_URL}/api/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: activePrompt, essay: fullEssay }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `Server returned ${res.status}`)
      }
      setGradeResult(await res.json())
    } catch (err) {
      setGradeError(err instanceof Error ? err.message : "Couldn't reach the backend. Is it running?")
      setGradeResult(null)
    } finally {
      setIsGrading(false)
    }
  }

  // Dictionary
  const [vocabTerm, setVocabTerm] = useState('')
  const [vocabResult, setVocabResult] = useState<DictionaryEntry | null>(null)
  const [vocabError, setVocabError] = useState<string | null>(null)
  const [isLookingUp, setIsLookingUp] = useState(false)
  async function lookupWord() {
    const term = vocabTerm.trim()
    if (!term || isLookingUp) return
    setIsLookingUp(true)
    setVocabError(null)
    try {
      const res = await fetch(`${API_URL}/api/vocab`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term, context: activePrompt }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `Server returned ${res.status}`)
      }
      setVocabResult(await res.json())
    } catch (err) {
      setVocabError(err instanceof Error ? err.message : "Couldn't reach the backend.")
      setVocabResult(null)
    } finally {
      setIsLookingUp(false)
    }
  }

  if (stage === 'topics') return <div className="page-view mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14"><div className="forest-appear forest-appear-delay-1 flex flex-wrap items-end justify-between gap-5"><div><p className="text-sm font-medium uppercase tracking-[0.18em] text-primary">Writing library</p><h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">Choose a topic.</h1><p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">Pick a Task 2 question to begin, or bring your own idea into the studio.</p></div><span className="rounded-full border border-border bg-secondary px-3 py-1.5 text-sm text-primary">Task 2 topic library</span></div><div className="topic-grid mt-10 forest-appear forest-appear-delay-2">{Object.entries(prompts).filter(([key]) => key !== 'custom').map(([key, item]) => <button key={key} onClick={() => { setPrompt(key as keyof typeof prompts); setStage('write') }} className="topic-card text-left"><span className="feature-number">TASK 2</span><h2>{item.label}</h2><p>{item.text}</p><span className="feature-link">Start practice <ArrowUpRight className="size-4" /></span></button>)}<div className="topic-card topic-card-custom"><span className="feature-number">YOUR IDEA</span><h2>Custom topic</h2><p>Write or paste your own IELTS Task 2 question, then enter the studio.</p><textarea value={customTopic} onChange={(event) => setCustomTopic(event.target.value)} placeholder="Type your topic here..." className="mt-4 min-h-24 w-full resize-y rounded-lg border border-border bg-card px-3 py-2 text-sm leading-6 text-primary outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring" aria-label="Custom topic" /><Button onClick={() => { if (customTopic.trim()) { setPrompt('custom'); setStage('write') } }} disabled={!customTopic.trim()} className="mt-4 gap-2">Use this topic <ArrowUpRight className="size-4" /></Button></div></div></div>
  return <div className="page-view mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-8"><div className="mb-6 forest-appear forest-appear-delay-1"><p className="text-sm font-medium uppercase tracking-[0.18em] text-primary">CtrlLang writing studio</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Make your argument count.</h1></div><div className="writing-grid"><Card className="writing-pane forest-appear forest-appear-delay-1"><CardHeader className="border-b border-border/70 px-5 py-4"><p className="text-sm font-semibold">Writing Task 2</p><p className="mt-2 text-sm italic leading-6 text-primary">{activePrompt}</p></CardHeader><CardContent className="flex flex-col gap-6 px-5 py-6"><div><p className="text-sm font-semibold text-primary">Writing focus</p><p className="mt-2 text-sm leading-6 text-muted-foreground">Paraphrase the question, state your position, then build each paragraph around one clear idea.</p></div><div className="writing-hints"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Writing hints</p><ul className="mt-3 flex flex-col gap-2 text-sm leading-6 text-primary"><li>• Make your opinion clear in the introduction.</li><li>• Support each body paragraph with a specific example.</li><li>• End by restating your position without adding a new idea.</li></ul></div></CardContent></Card><Card className="writing-pane forest-appear forest-appear-delay-2"><CardHeader className="flex-row items-center justify-between border-b border-border/70 px-5 py-4"><div className="flex items-center gap-3"><p className="text-sm font-semibold">Your answer</p><span className="rounded-full bg-secondary px-2.5 py-1 text-xs text-primary">Task 2</span><Button type="button" variant="outline" size="sm" onClick={randomizePrompt} className="gap-2"><Dices data-icon="inline-start" /> Randomize</Button></div><div className="flex items-center gap-3"><span className="text-sm text-primary">Word count: {wordCount}</span><button type="button" onClick={() => setShowSample(!showSample)} className={`sample-toggle ${showSample ? 'sample-toggle-on' : ''}`} aria-pressed={showSample}><span />Sample</button></div></CardHeader><CardContent className="flex flex-col gap-5 overflow-y-auto px-5 py-6">{showSample && <div className="sample-page"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Sample page</p><img src="/ielts-task-example.png" alt="Example IELTS task diagram" className="mt-3 w-full rounded-md border border-border/70" /><p className="mt-3 text-sm leading-7 text-primary">Learning a country&apos;s language and culture offers a deeper understanding of its people and traditions. Although travel provides valuable first-hand experience, structured study creates a stronger foundation for meaningful communication.</p></div>}{fields.map(([key, label]) => <label key={key} className="flex flex-col gap-2 text-sm font-semibold text-primary">{label}<Textarea value={essay[key]} onChange={(event) => update(key, event.target.value)} placeholder="Write your response here..." className={`writing-field ${key === 'overview' ? 'min-h-24' : 'min-h-32'} resize-y bg-card`} /></label>)}<Button className="self-start" disabled={!wordCount || isGrading} onClick={getFeedback}>{isGrading ? 'Grading…' : 'Get feedback'} <ArrowUpRight className="size-4" /></Button>{gradeError && <p className="text-sm text-destructive">{gradeError}</p>}{gradeResult && <div className="grading-result flex flex-col gap-5 rounded-lg border border-border bg-secondary/40 p-5"><div className="flex items-end justify-between border-b border-border/70 pb-4"><div><p className="text-xs text-muted-foreground">Estimated overall band</p><p className="mt-1 text-5xl leading-none text-primary">{gradeResult.band_estimate}</p></div><span className="text-xs text-muted-foreground">{gradeResult.source === 'heuristic' ? 'Rough estimate' : 'AI graded'}</span></div>{([['Task Achievement', gradeResult.task_achievement_band, gradeResult.task_achievement], ['Coherence & Cohesion', gradeResult.coherence_cohesion_band, gradeResult.coherence_cohesion], ['Lexical Resource', gradeResult.lexical_resource_band, gradeResult.lexical_resource], ['Grammar', gradeResult.grammar_band, gradeResult.grammar]] as const).map(([label, score, note]) => <div key={label} className="flex flex-col gap-1.5"><div className="flex items-center justify-between"><p className="text-sm font-semibold text-primary">{label}</p><span className="rounded-full bg-secondary px-2.5 py-0.5 text-sm text-primary">{score}</span></div><p className="text-sm leading-6 text-muted-foreground">{note}</p></div>)}<div className="rounded-lg border border-border bg-card p-4 text-sm leading-6 text-primary"><Sparkles className="mr-2 inline size-4" />Overall tip: {gradeResult.overall_tip}</div></div>}</CardContent></Card><Card className="writing-pane forest-appear forest-appear-delay-3"><CardHeader className="border-b border-border/70 px-5 py-4"><div className="flex items-center gap-2"><Sparkles className="size-4 text-primary" /><p className="text-sm font-semibold">Vocabulary helper</p><span className="size-2 rounded-full bg-accent" /></div></CardHeader><CardContent className="flex min-h-[320px] flex-col justify-between gap-4 px-5 py-6"><div className="flex flex-col gap-3 text-sm leading-6 text-muted-foreground">{!vocabResult && !vocabError && !isLookingUp && <div className="rounded-lg border border-border bg-secondary/60 p-4 text-primary"><p className="font-semibold">Try a phrase</p><p className="mt-1">“A balanced view is that…”</p></div>}{isLookingUp && <p className="text-primary">Looking up “{vocabTerm}”…</p>}{vocabError && <p className="text-destructive">{vocabError}</p>}{vocabResult && <div className="flex flex-col gap-3 rounded-lg border border-border bg-secondary/60 p-4 text-primary">
  <div className="flex items-center gap-2">
    <p className="font-semibold">{vocabResult.term || vocabTerm}</p>
    {vocabResult.part_of_speech && (
      <span className="rounded-full bg-card px-2 py-0.5 text-xs text-muted-foreground">
        {vocabResult.part_of_speech}
      </span>
    )}
  </div>
  <div>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Meaning</p>
    <p className="mt-1">{vocabResult.plain_meaning}</p>
  </div>
  {vocabResult.context_meaning && (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">In this context</p>
      <p className="mt-1 italic text-muted-foreground">{vocabResult.context_meaning}</p>
    </div>
  )}
  {vocabResult.example && (
    <p className="italic text-muted-foreground">“{vocabResult.example}”</p>
  )}
  {vocabResult.synonyms && vocabResult.synonyms.length > 0 && (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Synonyms</p>
      <p className="mt-1">{vocabResult.synonyms.join(', ')}</p>
    </div>
  )}
  {vocabResult.collocations && vocabResult.collocations.length > 0 && (
    <div className="border-t border-border pt-2">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Collocations</p>
      <ul className="mt-1 flex flex-col gap-1">
        {vocabResult.collocations.map((c, i) => (
          <li key={i}>
            <span className="font-medium">{c.phrase}</span>
            {c.example && <span className="italic text-muted-foreground"> - “{c.example}”</span>}
          </li>
        ))}
      </ul>
    </div>
  )}
</div>}</div><div className="border-t border-border pt-4"><p className="text-xs text-muted-foreground">Search vocabulary</p><div className="mt-2 flex items-center gap-2 rounded-lg border border-input px-3 py-2"><input value={vocabTerm} onChange={(event) => setVocabTerm(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && lookupWord()} placeholder="Type a phrase..." className="min-w-0 flex-1 bg-transparent text-sm text-primary outline-none placeholder:text-muted-foreground" /><button onClick={lookupWord} disabled={isLookingUp || !vocabTerm.trim()} aria-label="Search"><Search className="size-4 text-muted-foreground" /></button></div></div></CardContent></Card></div></div>
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
  return <main className="min-h-screen bg-background text-foreground forest-texture"><Header view={view} setView={setView} />{view === 'home' && <Home setView={setView} />}{view === 'reading' && <Reading />}{view === 'writing' && <WritingWorkspace />}<div className={`chat-widget ${chatOpen ? 'chat-widget-open' : ''}`}>{chatOpen && <div className="chat-panel"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div><p className="text-sm font-semibold">CtrlLang guide</p><p className="text-xs text-muted-foreground">Ask about your practice</p></div><button onClick={() => setChatOpen(false)} aria-label="Close chat"><X className="size-4" /></button></div><div className="flex min-h-24 flex-col justify-end gap-2 p-4"><p className="rounded-lg bg-secondary px-3 py-2 text-sm leading-5 text-primary">Need a starting point? Try reading the prompt aloud before you write.</p></div><div className="flex gap-2 border-t border-border p-3"><input aria-label="Chat message" placeholder="Ask CtrlLang..." className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none" /><Button size="icon" aria-label="Send message"><Send className="size-4" /></Button></div></div>}<button className="chat-bubble" onClick={() => setChatOpen(!chatOpen)} aria-label={chatOpen ? 'Close chat' : 'Open chat'}>{chatOpen ? <X className="size-5" /> : <MessageCircle className="size-5" />}</button></div></main>
}
