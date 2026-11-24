import { createSignal, createStore, For, onSettled, Show } from 'solid-js'
import { useNavigate } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { plural } from '../lib/format'
import { Confirm, ErrorPanel, Icon, IconButton, PageLoading, Spinner } from '../components/ui'

export default function Workouts() {
  const app = useApp()
  const navigate = useNavigate()

  const [page, setPage] = createStore({
    loaded: false,
    error: '',
    workouts: [],
    lastSession: null,
  })
  const [confirmDelete, setConfirmDelete] = createSignal(null)
  const [starting, setStarting] = createSignal(null)
  const [adding, setAdding] = createSignal(false)
  const [newName, setNewName] = createSignal('')
  const [saving, setSaving] = createSignal(false)

  async function load() {
    try {
      const data = await api.get('/workouts')
      setPage((p) => {
        p.workouts = data.workouts
        p.lastSession = data.last_session
        p.error = ''
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

  async function start(workout) {
    if (workout.active_session_id) {
      navigate(`/workout/${workout.workout_id}/session/${workout.active_session_id}`)
      return
    }
    setStarting(workout.workout_id)
    try {
      const data = await api.post(`/workouts/${workout.workout_id}/sessions`)
      navigate(`/workout/${workout.workout_id}/session/${data.workout_session.workout_session_id}`)
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setStarting(null)
    }
  }

  async function remove(workout) {
    try {
      await api.delete(`/workouts/${workout.workout_id}`)
      setConfirmDelete(null)
      app.notify(`Deleted "${workout.name}".`, 'success')
      await load()
    } catch (err) {
      app.notify(err.message, 'error')
    }
  }

  async function add(e) {
    e.preventDefault()
    if (!newName().trim()) return
    setSaving(true)
    try {
      const data = await api.post('/workouts', { name: newName().trim() })
      navigate(`/workout/${data.workout.workout_id}`)
    } catch (err) {
      app.notify(err.message, 'error')
      setSaving(false)
    }
  }

  return (
    <Show when={page.loaded} fallback={<PageLoading />}>
      <Show when={!page.error} fallback={<ErrorPanel message={page.error} onRetry={load} />}>
        <Show when={page.lastSession}>
          {(last) => (
            <section class="mb-6">
              <p class="eyebrow px-1">Last workout</p>
              <div class="card card-muted flex items-center justify-between gap-4">
                <div class="min-w-0">
                  <h2 class="truncate text-xl font-bold">{last().name}</h2>
                  <p class="muted text-sm">Done: {last().finished}</p>
                </div>
                <div class="flex gap-2">
                  <IconButton
                    icon="receipt_long"
                    label="Summary"
                    onClick={() =>
                      navigate(`/workout/${last().workout_id}/session/${last().workout_session_id}`)
                    }
                  />
                  <IconButton
                    icon="show_chart"
                    label="Progress"
                    onClick={() => navigate(`/workout/${last().workout_id}/logs`)}
                  />
                </div>
              </div>
            </section>
          )}
        </Show>

        <p class="eyebrow px-1">Workouts</p>
        <div class="grid gap-4 lg:grid-cols-3">
          <For
            each={page.workouts}
            fallback={<p class="muted card">You don't have any workouts yet. Add one below.</p>}
          >
            {(workout) => (
              <article class="card flex flex-col gap-4">
                <a href={`/workout/${workout.workout_id}`} class="block min-w-0">
                  <h2 class="truncate text-2xl font-bold">{workout.name}</h2>
                  <p class="muted">{plural(workout.exercise_count, 'exercise')}</p>
                </a>
                <div class="flex items-center justify-between gap-2">
                  <IconButton
                    icon="delete"
                    label="Delete workout"
                    onClick={() => setConfirmDelete(workout.workout_id)}
                  />
                  <div class="flex gap-2">
                    <IconButton
                      icon="show_chart"
                      label="Progress"
                      onClick={() => navigate(`/workout/${workout.workout_id}/logs`)}
                    />
                    <IconButton
                      icon="edit"
                      label="Edit workout"
                      onClick={() => navigate(`/workout/${workout.workout_id}`)}
                    />
                    <button
                      type="button"
                      class={['button-good start-button', { 'flashing-good': !!workout.active_session_id }]}
                      disabled={starting() === workout.workout_id || workout.exercise_count === 0}
                      title={workout.exercise_count === 0 ? 'Add an exercise first' : ''}
                      onClick={() => start(workout)}
                    >
                      <Show when={starting() !== workout.workout_id} fallback={<Spinner small />}>
                        <Icon name="play_arrow" />
                        {workout.active_session_id ? 'Resume' : 'Start'}
                      </Show>
                    </button>
                  </div>
                </div>
                <Show when={confirmDelete() === workout.workout_id}>
                  <Confirm
                    message="Delete this workout and all of its logs?"
                    confirmLabel="Delete"
                    onConfirm={() => remove(workout)}
                    onCancel={() => setConfirmDelete(null)}
                  />
                </Show>
              </article>
            )}
          </For>
        </div>

        <div class="mt-6">
          <Show
            when={adding()}
            fallback={
              <button type="button" class="add-button" onClick={() => setAdding(true)}>
                <Icon name="add" /> Workout
              </button>
            }
          >
            <form class="card flex flex-col gap-4" onSubmit={add}>
              <label class="flex flex-col gap-1">
                <span class="field-label">Workout name</span>
                <input
                  type="text"
                  maxlength="255"
                  placeholder="e.g. Push day"
                  ref={(el) => setTimeout(() => el.focus())}
                  value={newName()}
                  onInput={(e) => setNewName(e.currentTarget.value)}
                />
              </label>
              <div class="flex gap-4">
                <button
                  type="button"
                  class="flex-1"
                  onClick={() => {
                    setAdding(false)
                    setNewName('')
                  }}
                >
                  Cancel
                </button>
                <button type="submit" class="button-good flex-1" disabled={saving() || !newName().trim()}>
                  {saving() ? <Spinner small /> : 'Add'}
                </button>
              </div>
            </form>
          </Show>
        </div>
      </Show>
    </Show>
  )
}
