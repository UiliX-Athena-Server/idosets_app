import { createSignal, onSettled, Show } from 'solid-js'
import { useNavigate, useParams } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { PageLoading } from '../components/ui'

export default function Auth() {
  const app = useApp()
  const params = useParams()
  const navigate = useNavigate()
  const [failed, setFailed] = createSignal('')

  onSettled(() => {
    api
      .post('/auth', { account_id: params.account_id, auth_code: params.auth_code })
      .then((data) => {
        app.applySession(data)
        navigate('/workouts', { replace: true })
      })
      .catch((err) => setFailed(err.message))
  })

  return (
    <Show when={failed()} fallback={<PageLoading message="Logging in..." />}>
      <main class="narrow text-center">
        <h1 class="page-title my-8">💪 I Do Sets</h1>
        <div class="card flex flex-col gap-4">
          <p>{failed()}</p>
          <p class="muted">Login links last 30 days, and only the newest one works.</p>
          <a class="button" href="/login">
            Back to log in
          </a>
        </div>
      </main>
    </Show>
  )
}
