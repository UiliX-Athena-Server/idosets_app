import { createEffect, createMemo, createSignal, Match, Switch } from 'solid-js'
import { useNavigate } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { Spinner } from '../components/ui'
import EmailLimitNotice from '../components/EmailLimitNotice'
import Footer from '../components/Footer'

export default function Login() {
  const app = useApp()
  const navigate = useNavigate()

  const [email, setEmail] = createSignal('')
  const [status, setStatus] = createSignal('idle') // idle | sending | sent | error
  const [error, setError] = createSignal('')
  const [rateLimit, setRateLimit] = createSignal('')

  const alreadyLoggedIn = createMemo(() => app.state.ready && app.state.loggedIn)
  createEffect(
    () => alreadyLoggedIn(),
    (yes) => {
      if (yes) navigate('/workouts', { replace: true })
    },
  )

  async function submit(e) {
    e.preventDefault()
    if (!email().trim()) return
    setStatus('sending')
    setError('')
    setRateLimit('')
    try {
      await api.post('/login', { email_address: email().trim() })
      setStatus('sent')
    } catch (err) {
      if (err.kind === 'rate_limited') {
        setRateLimit(err.message)
        app.notify(err.message, 'warning', 10000)
      } else {
        setError(err.message)
      }
      setStatus('error')
    }
  }

  return (
    <main class="narrow">
      <h1 class="page-title text-center my-8">💪 I Do Sets</h1>

      <Switch>
        <Match when={status() === 'sent'}>
          <div class="card flex flex-col gap-3 text-center">
            <p class="font-bold">Check your inbox!</p>
            <p>Your login link has been emailed to {email()}.</p>
            <p class="muted">Remember to check your spam folder.</p>
            <button type="button" onClick={() => setStatus('idle')}>
              Use a different email
            </button>
          </div>
        </Match>
        <Match when={status() !== 'sent'}>
          <form class="flex flex-col gap-4" onSubmit={submit}>
            <EmailLimitNotice message={rateLimit()} />
            <label class="flex flex-col gap-1">
              <span class="field-label">Email address</span>
              <input
                type="email"
                name="email_address"
                autocomplete="email"
                required
                placeholder="you@example.com"
                value={email()}
                onInput={(e) => setEmail(e.currentTarget.value)}
              />
            </label>
            <p class="error-text">{error()}</p>
            <button type="submit" class="button-good button-large" disabled={status() === 'sending'}>
              {status() === 'sending' ? <Spinner small /> : 'Log in / Sign up'}
            </button>
            <p class="muted text-sm text-center">
              No password needed, we'll email you a login link.
            </p>
          </form>
        </Match>
      </Switch>

      <Footer />
    </main>
  )
}
