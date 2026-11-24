import { createSignal, Match, Switch } from 'solid-js'
import { useParams } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { Spinner } from '../components/ui'

export default function DeleteAccount() {
  const app = useApp()
  const params = useParams()
  const [status, setStatus] = createSignal('confirm') // confirm | deleting | deleted | error
  const [error, setError] = createSignal('')

  async function remove() {
    setStatus('deleting')
    try {
      await api.post('/account/delete', {
        account_id: params.account_id,
        auth_code: params.auth_code,
      })
      await app.loadSession()
      setStatus('deleted')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  return (
    <main class="narrow text-center">
      <h1 class="page-title my-8">💪 I Do Sets</h1>
      <div class="card flex flex-col gap-4">
        <Switch>
          <Match when={status() === 'confirm' || status() === 'deleting'}>
            <p class="font-bold">Delete your account?</p>
            <p>
              This permanently deletes your email address, workouts and workout logs. It can't be
              undone.
            </p>
            <button
              type="button"
              class="button-bad button-large"
              disabled={status() === 'deleting'}
              onClick={remove}
            >
              {status() === 'deleting' ? <Spinner small /> : 'Yes, delete my account'}
            </button>
            <a class="button" href="/workouts">
              Keep my account
            </a>
          </Match>
          <Match when={status() === 'deleted'}>
            <p>Your account has been deleted.</p>
            <a class="button" href="/">
              Done
            </a>
          </Match>
          <Match when={status() === 'error'}>
            <p>{error()}</p>
            <a class="button" href="/account">
              Back to your account
            </a>
          </Match>
        </Switch>
      </div>
    </main>
  )
}
