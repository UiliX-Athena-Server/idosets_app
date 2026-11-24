import { createSignal, createStore, onSettled, Show } from 'solid-js'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { Confirm, ErrorPanel, Icon, PageHeader, PageLoading } from '../components/ui'
import EmailLimitNotice from '../components/EmailLimitNotice'
import ThemeToggle from '../components/ThemeToggle'

export default function Account() {
  const app = useApp()
  const [page, setPage] = createStore({ loaded: false, error: '', info: null })
  const [confirmDelete, setConfirmDelete] = createSignal(false)
  const [deleteSent, setDeleteSent] = createSignal(false)
  const [rateLimit, setRateLimit] = createSignal('')
  const [savingUnits, setSavingUnits] = createSignal(false)

  async function load() {
    setPage((p) => {
      p.error = ''
    })
    try {
      const info = await api.get('/account')
      setPage((p) => {
        p.info = info
        p.loaded = true
      })
    } catch (err) {
      setPage((p) => {
        p.error = err.message
        p.loaded = true
      })
    }
  }

  onSettled(() => {
    load()
  })

  async function setUnits(units) {
    if (units === app.state.units) return
    setSavingUnits(true)
    try {
      await app.saveSettings({ units })
      app.notify(`Weights will now be shown in ${units === 'lbs' ? 'pounds' : 'kilograms'}.`, 'success')
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setSavingUnits(false)
    }
  }

  async function requestDelete() {
    setRateLimit('')
    try {
      await api.post('/account/delete/request')
      setDeleteSent(true)
      setConfirmDelete(false)
    } catch (err) {
      setConfirmDelete(false)
      if (err.kind === 'rate_limited') {
        setRateLimit(err.message)
        app.notify(err.message, 'warning', 10000)
      } else {
        app.notify(err.message, 'error')
      }
    }
  }

  return (
    <>
      <PageHeader title="Account" />
      <Show when={page.loaded} fallback={<PageLoading />}>
        <Show when={!page.error} fallback={<ErrorPanel message={page.error} onRetry={load} />}>
          <div class="flex flex-col gap-4">
            <section class="card flex flex-col gap-2">
              <p class="eyebrow">Your account</p>
              <p class="break-all">{page.info.email_address}</p>
              <div class="stats">
                <div>
                  <strong>{page.info.total_workouts}</strong>
                  <span>Workouts</span>
                </div>
                <div>
                  <strong>{page.info.total_exercises}</strong>
                  <span>Exercises</span>
                </div>
                <div>
                  <strong>{page.info.total_sets}</strong>
                  <span>Sets</span>
                </div>
              </div>
            </section>

            <section class="card flex items-center justify-between gap-4">
              <div>
                <p class="font-bold">Theme</p>
                <p class="muted text-sm">Currently {app.state.theme}.</p>
              </div>
              <ThemeToggle />
            </section>

            <section class="card flex flex-wrap items-center justify-between gap-4">
              <div>
                <p class="font-bold">Weight units</p>
                <p class="muted text-sm">Used when logging and showing weights.</p>
              </div>
              <div class="segmented" role="group" aria-label="Weight units">
                <button
                  type="button"
                  class={{ active: app.state.units === 'kgs' }}
                  disabled={savingUnits()}
                  onClick={() => setUnits('kgs')}
                >
                  kg
                </button>
                <button
                  type="button"
                  class={{ active: app.state.units === 'lbs' }}
                  disabled={savingUnits()}
                  onClick={() => setUnits('lbs')}
                >
                  lbs
                </button>
              </div>
            </section>

            <section class="card card-warning flex flex-col gap-4">
              <p class="font-bold">Delete account</p>
              <EmailLimitNotice message={rateLimit()} />
              <Show
                when={!deleteSent()}
                fallback={
                  <p>
                    <Icon name="mark_email_read" class="align-middle" /> We've emailed you a link to
                    confirm deleting your account. It's valid for 24 hours.
                  </p>
                }
              >
                <Show
                  when={confirmDelete()}
                  fallback={
                    <button type="button" class="button-bad self-start" onClick={() => setConfirmDelete(true)}>
                      Delete account
                    </button>
                  }
                >
                  <Confirm
                    message="We'll email you a link to confirm. Continue?"
                    confirmLabel="Send email"
                    cancelLabel="Cancel"
                    onConfirm={requestDelete}
                    onCancel={() => setConfirmDelete(false)}
                  />
                </Show>
              </Show>
            </section>
          </div>
        </Show>
      </Show>
    </>
  )
}
