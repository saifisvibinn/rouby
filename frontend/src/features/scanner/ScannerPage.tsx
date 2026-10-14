import { Minus, Plus } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  pairScannerRequest,
  submitScanEventRequest,
  type ScanEventResponse,
  type ScannerPairResponse,
} from '@/lib/api'

type Feedback =
  | { tone: 'idle'; message: string }
  | { tone: 'success'; message: string }
  | { tone: 'warning'; message: string }
  | { tone: 'error'; message: string }

const deviceStorageKey = 'rouby_scanner_device'

export const ScannerPage = () => {
  const [searchParams] = useSearchParams()
  const pairToken = searchParams.get('pair')
  const [pairing, setPairing] = useState<ScannerPairResponse | null>(() => {
    const saved = sessionStorage.getItem(deviceStorageKey)
    return saved ? (JSON.parse(saved) as ScannerPairResponse) : null
  })
  const [code, setCode] = useState('')
  const [qty, setQty] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>({
    tone: 'idle',
    message: 'Pair this device from the POS QR code, then enter a barcode manually.',
  })
  const [lastScan, setLastScan] = useState<ScanEventResponse | null>(null)

  useEffect(() => {
    if (!pairToken) {
      return
    }

    let isCancelled = false
    const pairDevice = async () => {
      try {
        const paired = await pairScannerRequest(pairToken)
        if (isCancelled) {
          return
        }
        setPairing(paired)
        sessionStorage.setItem(deviceStorageKey, JSON.stringify(paired))
        setFeedback({ tone: 'success', message: `Paired in ${paired.mode} mode.` })
      } catch {
        if (!isCancelled) {
          setFeedback({ tone: 'error', message: 'Pairing failed or the QR code expired.' })
        }
      }
    }

    void pairDevice()
    return () => {
      isCancelled = true
    }
  }, [pairToken])

  const feedbackClassName = useMemo(() => {
    if (feedback.tone === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-800'
    if (feedback.tone === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800'
    if (feedback.tone === 'error') return 'border-red-200 bg-red-50 text-red-800'
    return 'border-stone-200 bg-stone-50 text-stone-700'
  }, [feedback.tone])

  const handleQtyChange = (nextQty: number) => {
    setQty(Math.max(1, Math.min(999, nextQty)))
  }

  const handleSubmit = async () => {
    if (!pairing) {
      setFeedback({ tone: 'error', message: 'Pair this scanner before submitting scans.' })
      return
    }
    const trimmedCode = code.trim()
    if (!trimmedCode) {
      setFeedback({ tone: 'warning', message: 'Enter a barcode or batch code first.' })
      return
    }

    setIsSubmitting(true)
    try {
      const result = await submitScanEventRequest(pairing.device_token, {
        event_id: crypto.randomUUID(),
        code: trimmedCode,
        qty,
      })
      setLastScan(result)
      setCode('')
      setFeedback({
        tone: result.duplicate ? 'warning' : 'success',
        message: result.resolved
          ? `${result.resolved.name_en} x ${qty} sent to ${result.mode}.`
          : result.message,
      })
    } catch {
      setFeedback({ tone: 'error', message: 'Code not found or scanner session expired.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmitForm = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void handleSubmit()
  }

  return (
    <main className="min-h-dvh bg-stone-950 px-4 py-6 text-stone-50 safe-top pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto flex min-h-[calc(100dvh-3rem)] w-full max-w-md flex-col gap-4">
        <header className="space-y-2">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-teal-300">Rouby</p>
          <h1 className="text-3xl font-semibold">Phone Scanner</h1>
          <p className="text-sm text-stone-300">
            Camera scanning is not bundled yet. Use manual entry for this Phase 3B scanner.
          </p>
        </header>

        <Card className="space-y-4 bg-white text-stone-950">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-stone-500">Mode</p>
              <p className="text-2xl font-semibold">{pairing?.mode ?? 'Not paired'}</p>
            </div>
            <span className="rounded-full bg-teal-100 px-3 py-1 text-sm font-medium text-teal-800">
              {pairing ? 'Ready' : 'Waiting'}
            </span>
          </div>

          <div className={`rounded-xl border p-3 text-sm ${feedbackClassName}`} role="status">
            {feedback.message}
          </div>

          <form className="space-y-4" onSubmit={handleSubmitForm}>
            <div className="space-y-2">
              <label htmlFor="scanner-code" className="text-sm font-medium text-stone-700">
                Barcode or batch code
              </label>
              <Input
                id="scanner-code"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="Scan or type code"
                autoComplete="off"
                inputMode="text"
                className="h-14 text-lg"
              />
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-stone-700">Quantity</p>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="lg"
                  className="h-14 w-14 rounded-full p-0"
                  onClick={() => handleQtyChange(qty - 1)}
                  aria-label="Decrease quantity"
                >
                  <Minus className="h-5 w-5" />
                </Button>
                <output className="flex h-14 flex-1 items-center justify-center rounded-xl border border-stone-200 text-2xl font-semibold">
                  {qty}
                </output>
                <Button
                  variant="outline"
                  size="lg"
                  className="h-14 w-14 rounded-full p-0"
                  onClick={() => handleQtyChange(qty + 1)}
                  aria-label="Increase quantity"
                >
                  <Plus className="h-5 w-5" />
                </Button>
              </div>
            </div>

            <Button type="submit" size="lg" className="h-14 w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Sending...' : 'Send scan'}
            </Button>
          </form>
        </Card>

        {lastScan?.resolved ? (
          <Card className="bg-stone-900 text-stone-50">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-stone-400">Last scan</p>
            <p className="mt-2 text-xl font-semibold">{lastScan.resolved.name_en}</p>
            <p className="mt-1 text-sm text-stone-300">
              {lastScan.resolved.type} {lastScan.resolved.sku ? `- ${lastScan.resolved.sku}` : ''}
            </p>
          </Card>
        ) : null}
      </div>
    </main>
  )
}
