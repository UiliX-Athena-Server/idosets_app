import { createSignal, createStore, For, onSettled, Show } from 'solid-js'
import { useNavigate, useParams } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { formatClock, formatDuration, formatNumber, unitLabel } from '../lib/format'
import { clearAllPending, clearPending, readPending, setPending } from '../lib/pending'
import {
  Confirm,
  ErrorPanel,
  Icon,
  InstructionsLink,
  PageHeader,
  PageLoading,
  Spinner,
} from '../components/ui'
import SetCard, { describeLog } from '../components/SetCard'

export default function Session() {
  const app = useApp()
  const params = useParams()
  const navigate = useNavigate()

  const [page, setPage] = createStore({
    loaded: false,
    error: '',
    workout: null,
    session: null,
    exercises: [],
    units: 'kgs',
  })
  const [openSet, setOpenSet] = createSignal(null)
  const [copying, setCopying] = createSignal(null)
  const [offline, setOffline] = createSignal(false)
  const [finish, setFinish] = createSignal('idle') // idle | confirm | saving | error
  const [finishError, setFinishError] = createSignal('')
  const [confirmCancel, setConfirmCancel] = createSignal(false)
  const [now, setNow] = createSignal(Date.now())
  let loadedAt = Date.now()

  const sessionId = () => params.workout_session_id
  const base = () => `/workouts/${params.workout_id}/sessions/${params.workout_session_id}`

  // -- helpers ----------------------------------------------------------------

  function findSet(setId) {
    for (const exercise of page.exercises) {
      const set = exercise.sets.find((s) => s.set_id === setId)
      if (set) return set
    }
    return null
  }

  function updateSet(setId, fn) {
    setPage((p) => {
      for (const exercise of p.exercises) {
        const set = exercise.sets.find((s) => s.set_id === setId)
        if (set) fn(set)
      }
    })
  }

  function applyPayload(data) {
    loadedAt = Date.now()
    setPage((p) => {
      p.workout = data.workout
      p.session = data.workout_session
      p.exercises = data.exercises
      p.units = data.units
      p.error = ''
      p.loaded = true
    })
  }

  const elapsed = () => (page.session?.duration || 0) + Math.floor((now() - loadedAt) / 1000)
  const setsTotal = () => page.exercises.reduce((n, e) => n + e.sets.length, 0)
  const setsDone = () =>
    page.exercises.reduce((n, e) => n + e.sets.filter((s) => s.set_log).length, 0)

  // -- loading & syncing --------------------------------------------------------

  async function load() {
    try {
      const data = await api.get(base())
      applyPayload(data)
      if (!data.workout_session.is_finished) {
        // Re-apply anything logged on this device that never reached the server.
        const pending = readPending(sessionId())
        for (const [setId, values] of Object.entries(pending)) {
          updateSet(Number(setId), (set) => {
            set.set_log = values ? { ...values, pending: true } : null
          })
        }
        syncPending()
      } else {
        clearAllPending(sessionId())
      }
    } catch (err) {
      setPage((p) => {
        p.error = err.message
        p.loaded = true
      })
    }
  }

  async function syncPending() {
    const pending = readPending(sessionId())
    for (const [setId, values] of Object.entries(pending)) {
      try {
        if (values) {
          const data = await api.put(`${base()}/sets/${setId}/log`, values)
          updateSet(Number(setId), (set) => {
            set.set_log = data.set_log
          })
        } else {
          await api.delete(`${base()}/sets/${setId}/log`)
        }
        clearPending(sessionId(), setId)
      } catch (err) {
        if (err.isNetwork) {
          setOffline(true)
          return
        }
        // The server rejected it (e.g. set deleted); drop it.
        clearPending(sessionId(), setId)
      }
    }
    setOffline(false)
  }

  onSettled(() => {
    load()
    const tick = setInterval(() => setNow(Date.now()), 1000)
    const online = () => syncPending()
    window.addEventListener('online', online)
    return () => {
      clearInterval(tick)
      window.removeEventListener('online', online)
    }
  })

  // -- set actions --------------------------------------------------------------

  async function logSet(setId, values) {
    setOpenSet(null)
    updateSet(setId, (set) => {
      set.set_log = { ...values, pending: true }
    })
    setPending(sessionId(), setId, values)
    scrollToNext(setId)

    try {
      const data = await api.put(`${base()}/sets/${setId}/log`, values)
      updateSet(setId, (set) => {
        set.set_log = data.set_log
      })
      clearPending(sessionId(), setId)
      setOffline(false)
    } catch (err) {
      if (err.isNetwork) {
        if (!offline()) {
          app.notify("You're offline. Sets are saved on this phone and will sync later.", 'warning')
        }
        setOffline(true)
      } else if (err.status === 409) {
        clearPending(sessionId(), setId)
        load()
      } else {
        app.notify(err.message, 'error')
      }
    }
  }

  async function undoSet(setId) {
    const previous = findSet(setId)?.set_log
    updateSet(setId, (set) => {
      set.set_log = null
    })
    setPending(sessionId(), setId, null)
    try {
      await api.delete(`${base()}/sets/${setId}/log`)
      clearPending(sessionId(), setId)
    } catch (err) {
      if (err.isNetwork) {
        setOffline(true)
      } else {
        clearPending(sessionId(), setId)
        updateSet(setId, (set) => {
          set.set_log = previous
        })
        app.notify(err.message, 'error')
      }
    }
  }

  async function copySet(exercise, set) {
    setCopying(set.set_id)
    try {
      const data = await api.post(
        `/workouts/${params.workout_id}/exercises/${exercise.exercise_id}/sets/${set.set_id}/copy`,
      )
      setPage((p) => {
        const target = p.exercises.find((e) => e.exercise_id === exercise.exercise_id)
        const index = target.sets.findIndex((s) => s.set_id === set.set_id)
        target.sets.splice(index + 1, 0, { ...data.set, set_log: null, previous_log: null })
      })
      app.notify('Added another set. It will be in this workout from now on.', 'success', 3500)
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setCopying(null)
    }
  }

  function scrollToNext(setId) {
    const all = page.exercises.flatMap((e) => e.sets)
    const index = all.findIndex((s) => s.set_id === setId)
    const next = all.slice(index + 1).find((s) => !s.set_log)
    if (!next) return
    setTimeout(() => {
      document
        .getElementById(`set-${next.set_id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)
  }

  // -- finish / cancel ----------------------------------------------------------

  async function finishWorkout() {
    setFinish('saving')
    setFinishError('')
    const logs = page.exercises
      .flatMap((e) => e.sets)
      .filter((s) => s.set_log)
      .map((s) => ({
        set_id: s.set_id,
        reps: s.set_log.reps,
        weight: s.set_log.weight,
        duration: s.set_log.duration,
      }))

    try {
      // The client's list is the full record (covers anything logged or
      // undone while offline). Safe to retry: the server finishes only once.
      const data = await api.post(`${base()}/finish`, { logs, replace: true }, { timeout: 30000 })
      clearAllPending(sessionId())
      setOffline(false)
      applyPayload(data)
      setFinish('idle')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      setFinishError(
        err.isNetwork
          ? "Couldn't reach the server. Your sets are safe on this phone, try again when you have signal."
          : err.message,
      )
      setFinish('error')
    }
  }

  async function cancelWorkout() {
    try {
      await api.delete(base())
      clearAllPending(sessionId())
      navigate('/workouts', { replace: true })
    } catch (err) {
      app.notify(err.message, 'error')
    }
  }

  // -- views --------------------------------------------------------------------

  function InProgress() {
    return (
      <>
        <PageHeader back="/workouts" eyebrow="Workout in progress" title={page.workout.name} />

        <div class="session-bar">
          <span>
            <Icon name="timer" /> {formatClock(elapsed())}
          </span>
          <span>
            <Icon name="done_all" /> {setsDone()} / {setsTotal()} sets
          </span>
          <Show when={offline()}>
            <span class="flashing-warning-color" title="Offline, sets are saved on this phone">
              <Icon name="cloud_off" /> Offline
            </span>
          </Show>
        </div>

        <div class="flex flex-col gap-6">
          <For each={page.exercises}>
            {(exercise) => (
              <section class="exercise-block">
                <div class="mb-3 px-1">
                  <h2 class="text-2xl font-bold">{exercise.name}</h2>
                  <InstructionsLink url={exercise.info_url} favicon={exercise.info_url_favicon} />
                </div>
                <div class="flex flex-col gap-3">
                  <For each={exercise.sets} fallback={<p class="muted px-1">No sets in this exercise.</p>}>
                    {(set, index) => (
                      <SetCard
                        set={set}
                        index={index()}
                        units={page.units}
                        open={openSet() === set.set_id}
                        finished={false}
                        copying={copying() === set.set_id}
                        onOpen={() => setOpenSet(set.set_id)}
                        onClose={() => setOpenSet(null)}
                        onLog={(values) => logSet(set.set_id, values)}
                        onUndo={() => undoSet(set.set_id)}
                        onCopy={() => copySet(exercise, set)}
                      />
                    )}
                  </For>
                </div>
              </section>
            )}
          </For>
        </div>

        <section class="my-10 flex flex-col gap-4">
          <Show
            when={finish() !== 'idle'}
            fallback={
              <button type="button" class="button-good button-large" onClick={() => setFinish('confirm')}>
                <Icon name="flag" /> Finish workout
              </button>
            }
          >
            <div class="card flex flex-col gap-4 text-center">
              <Show when={finish() === 'error'}>
                <p class="error-text">{finishError()}</p>
              </Show>
              <Show when={finish() === 'confirm'}>
                <p>
                  Finish this workout?
                  <Show when={setsDone() < setsTotal()}>
                    {' '}
                    You've done {setsDone()} of {setsTotal()} sets.
                  </Show>
                </p>
              </Show>
              <div class="flex gap-3">
                <button
                  type="button"
                  class="button-good flex-1"
                  disabled={finish() === 'saving'}
                  onClick={finishWorkout}
                >
                  <Show when={finish() !== 'saving'} fallback={<Spinner small />}>
                    {finish() === 'error' ? 'Try again' : 'Finish'}
                  </Show>
                </button>
                <button
                  type="button"
                  class="flex-1"
                  disabled={finish() === 'saving'}
                  onClick={() => setFinish('idle')}
                >
                  Keep going
                </button>
              </div>
            </div>
          </Show>

          <Show
            when={confirmCancel()}
            fallback={
              <button type="button" class="button-ghost" onClick={() => setConfirmCancel(true)}>
                Cancel workout
              </button>
            }
          >
            <Confirm
              message="Cancel this workout? Everything logged in it will be discarded."
              confirmLabel="Discard workout"
              cancelLabel="Keep it"
              onConfirm={cancelWorkout}
              onCancel={() => setConfirmCancel(false)}
            />
          </Show>
        </section>
      </>
    )
  }

  function Summary() {
    return (
      <>
        <PageHeader
          back="/workouts"
          eyebrow={`Workout finished · ${page.session.finished_display}`}
          title={page.workout.name}
        />

        <div class="stats card mb-6">
          <div>
            <strong>{formatDuration(page.session.duration)}</strong>
            <span>Time</span>
          </div>
          <div>
            <strong>
              {page.session.sets_done} / {page.session.sets_total}
            </strong>
            <span>Sets</span>
          </div>
          <Show when={page.session.total_weight > 0}>
            <div>
              <strong>
                {formatNumber(page.session.total_weight)} {unitLabel(page.units)}
              </strong>
              <span>Total weight lifted</span>
            </div>
          </Show>
        </div>

        <div class="flex flex-col gap-4">
          <For each={page.exercises}>
            {(exercise) => (
              <section class="card">
                <h2 class="mb-2 text-xl font-bold">{exercise.name}</h2>
                <ol class="summary-sets">
                  <For each={exercise.sets}>
                    {(set, index) => (
                      <li class={{ muted: !set.set_log }}>
                        <span class="set-number">{index() + 1}</span>
                        {set.set_log ? describeLog(set.set_log, set, page.units) : 'Skipped'}
                      </li>
                    )}
                  </For>
                </ol>
              </section>
            )}
          </For>
        </div>

        <div class="my-8 flex flex-wrap gap-3">
          <a class="button button-good button-large flex-1" href="/workouts">
            Done
          </a>
          <a class="button button-large flex-1" href={`/workout/${params.workout_id}/logs`}>
            <Icon name="show_chart" /> See progress
          </a>
        </div>
      </>
    )
  }

  return (
    <Show when={page.loaded} fallback={<PageLoading />}>
      <Show when={!page.error} fallback={<ErrorPanel message={page.error} onRetry={load} />}>
        <Show when={page.session.is_finished} fallback={<InProgress />}>
          <Summary />
        </Show>
      </Show>
    </Show>
  )
}
