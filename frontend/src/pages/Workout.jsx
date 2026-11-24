import { createSignal, createStore, For, onSettled, Show } from 'solid-js'
import { useNavigate, useParams } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { plural } from '../lib/format'
import {
  Confirm,
  ErrorPanel,
  Icon,
  IconButton,
  InstructionsLink,
  PageHeader,
  PageLoading,
  Spinner,
} from '../components/ui'

export default function Workout() {
  const app = useApp()
  const params = useParams()
  const navigate = useNavigate()

  const [page, setPage] = createStore({ loaded: false, error: '', workout: null, exercises: [] })
  const [renaming, setRenaming] = createSignal(false)
  const [name, setName] = createSignal('')
  const [confirmDelete, setConfirmDelete] = createSignal(null)
  const [adding, setAdding] = createSignal(false)
  const [exerciseName, setExerciseName] = createSignal('')
  const [exerciseUrl, setExerciseUrl] = createSignal('')
  const [saving, setSaving] = createSignal(false)
  const [starting, setStarting] = createSignal(false)

  const base = () => `/workouts/${params.workout_id}`

  async function load() {
    try {
      const data = await api.get(base())
      setPage((p) => {
        p.workout = data.workout
        p.exercises = data.exercises
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

  async function rename(e) {
    e.preventDefault()
    if (!name().trim()) return
    setSaving(true)
    try {
      const data = await api.patch(base(), { name: name().trim() })
      setPage((p) => {
        p.workout.name = data.workout.name
      })
      setRenaming(false)
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function addExercise(e) {
    e.preventDefault()
    if (!exerciseName().trim()) return
    setSaving(true)
    try {
      const data = await api.post(`${base()}/exercises`, {
        name: exerciseName().trim(),
        info_url: exerciseUrl().trim(),
      })
      navigate(`/workout/${params.workout_id}/exercise/${data.exercise.exercise_id}`)
    } catch (err) {
      app.notify(err.message, 'error')
      setSaving(false)
    }
  }

  async function removeExercise(exercise) {
    try {
      await api.delete(`${base()}/exercises/${exercise.exercise_id}`)
      setConfirmDelete(null)
      setPage((p) => {
        const index = p.exercises.findIndex((x) => x.exercise_id === exercise.exercise_id)
        if (index !== -1) p.exercises.splice(index, 1)
      })
    } catch (err) {
      app.notify(err.message, 'error')
    }
  }

  async function start() {
    const active = page.workout.active_session_id
    if (active) {
      navigate(`/workout/${params.workout_id}/session/${active}`)
      return
    }
    setStarting(true)
    try {
      const data = await api.post(`${base()}/sessions`)
      navigate(`/workout/${params.workout_id}/session/${data.workout_session.workout_session_id}`)
    } catch (err) {
      app.notify(err.message, 'error')
      setStarting(false)
    }
  }

  return (
    <Show when={page.loaded} fallback={<PageLoading />}>
      <Show
        when={!page.error}
        fallback={<ErrorPanel message={page.error} onRetry={load} />}
      >
        <PageHeader back="/workouts" eyebrow="Workout" title={page.workout.name}>
          <IconButton
            icon="edit"
            label="Rename workout"
            onClick={() => {
              setName(page.workout.name)
              setRenaming(true)
            }}
          />
        </PageHeader>

        <Show when={renaming()}>
          <form class="card mb-4 flex flex-col gap-4" onSubmit={rename}>
            <label class="flex flex-col gap-1">
              <span class="field-label">Workout name</span>
              <input
                type="text"
                maxlength="255"
                value={name()}
                onInput={(e) => setName(e.currentTarget.value)}
              />
            </label>
            <div class="flex gap-4">
              <button type="button" class="flex-1" onClick={() => setRenaming(false)}>
                Cancel
              </button>
              <button type="submit" class="button-good flex-1" disabled={saving()}>
                Save
              </button>
            </div>
          </form>
        </Show>

        <div class="mb-6 flex flex-wrap gap-2">
          <button
            type="button"
            class="button-good button-large flex-1"
            disabled={starting() || page.exercises.length === 0}
            onClick={start}
          >
            <Show when={!starting()} fallback={<Spinner small />}>
              <Icon name="play_arrow" />
              {page.workout.active_session_id ? 'Resume workout' : 'Start workout'}
            </Show>
          </button>
          <a class="button button-large" href={`/workout/${params.workout_id}/logs`}>
            <Icon name="show_chart" /> Progress
          </a>
        </div>

        <p class="eyebrow px-1">Exercises</p>
        <div class="flex flex-col gap-4">
          <For
            each={page.exercises}
            fallback={<p class="card muted">No exercises yet. Add your first one below.</p>}
          >
            {(exercise) => (
              <article class="card flex flex-col gap-3">
                <div class="flex items-start justify-between gap-4">
                  <a
                    href={`/workout/${params.workout_id}/exercise/${exercise.exercise_id}`}
                    class="min-w-0 flex-1"
                  >
                    <h2 class="text-2xl font-bold">{exercise.name}</h2>
                    <p class="muted">{plural(exercise.set_count, 'set')}</p>
                  </a>
                  <div class="flex gap-2">
                    <IconButton
                      icon="delete"
                      label="Delete exercise"
                      onClick={() => setConfirmDelete(exercise.exercise_id)}
                    />
                    <IconButton
                      icon="chevron_right"
                      label="Edit sets"
                      onClick={() =>
                        navigate(`/workout/${params.workout_id}/exercise/${exercise.exercise_id}`)
                      }
                    />
                  </div>
                </div>
                <InstructionsLink url={exercise.info_url} favicon={exercise.info_url_favicon} />
                <Show when={confirmDelete() === exercise.exercise_id}>
                  <Confirm
                    message="Delete this exercise and its logs?"
                    confirmLabel="Delete"
                    onConfirm={() => removeExercise(exercise)}
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
                <Icon name="add" /> Exercise
              </button>
            }
          >
            <form class="card flex flex-col gap-4" onSubmit={addExercise}>
              <label class="flex flex-col gap-1">
                <span class="field-label">Exercise name</span>
                <input
                  type="text"
                  maxlength="255"
                  placeholder="e.g. Bench press"
                  ref={(el) => setTimeout(() => el.focus())}
                  value={exerciseName()}
                  onInput={(e) => setExerciseName(e.currentTarget.value)}
                />
              </label>
              <label class="flex flex-col gap-1">
                <span class="field-label">Instructions link (optional)</span>
                <input
                  type="url"
                  inputmode="url"
                  placeholder="https://..."
                  value={exerciseUrl()}
                  onInput={(e) => setExerciseUrl(e.currentTarget.value)}
                />
              </label>
              <div class="flex gap-4">
                <button
                  type="button"
                  class="flex-1"
                  onClick={() => {
                    setAdding(false)
                    setExerciseName('')
                    setExerciseUrl('')
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  class="button-good flex-1"
                  disabled={saving() || !exerciseName().trim()}
                >
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
