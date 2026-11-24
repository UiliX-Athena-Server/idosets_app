import { createSignal, createStore, For, onSettled, Show } from 'solid-js'
import { useParams } from '@solidjs/router'
import { api } from '../lib/api'
import { useApp } from '../lib/app'
import { setTarget } from '../lib/format'
import {
  Confirm,
  DurationField,
  ErrorPanel,
  Icon,
  IconButton,
  InstructionsLink,
  NumberField,
  PageHeader,
  PageLoading,
  Spinner,
} from '../components/ui'

const EMPTY_SET = { type: 'reps', repsMin: '', repsMax: '', durationMin: 0, durationMax: 0 }

export default function Exercise() {
  const app = useApp()
  const params = useParams()

  const [page, setPage] = createStore({
    loaded: false,
    error: '',
    workout: null,
    exercise: null,
    sets: [],
  })
  const [editing, setEditing] = createSignal(false)
  const [name, setName] = createSignal('')
  const [url, setUrl] = createSignal('')
  const [saving, setSaving] = createSignal(false)
  const [confirmDelete, setConfirmDelete] = createSignal(null)
  const [copying, setCopying] = createSignal(null)
  const [adding, setAdding] = createSignal(false)
  const [draft, setDraft] = createStore({ ...EMPTY_SET })

  const base = () => `/workouts/${params.workout_id}/exercises/${params.exercise_id}`

  async function load() {
    try {
      const data = await api.get(base())
      setPage((p) => {
        p.workout = data.workout
        p.exercise = data.exercise
        p.sets = data.sets
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

  async function save(e) {
    e.preventDefault()
    if (!name().trim()) return
    setSaving(true)
    try {
      const data = await api.patch(base(), { name: name().trim(), info_url: url().trim() })
      setPage((p) => {
        p.exercise = data.exercise
      })
      setEditing(false)
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function copySet(set) {
    setCopying(set.set_id)
    try {
      const data = await api.post(`${base()}/sets/${set.set_id}/copy`)
      setPage((p) => {
        const index = p.sets.findIndex((s) => s.set_id === set.set_id)
        p.sets.splice(index + 1, 0, data.set)
      })
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setCopying(null)
    }
  }

  async function deleteSet(set) {
    try {
      await api.delete(`${base()}/sets/${set.set_id}`)
      setConfirmDelete(null)
      setPage((p) => {
        const index = p.sets.findIndex((s) => s.set_id === set.set_id)
        if (index !== -1) p.sets.splice(index, 1)
      })
    } catch (err) {
      app.notify(err.message, 'error')
    }
  }

  async function addSet(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const data = await api.post(`${base()}/sets`, {
        type: draft.type,
        reps_min: Number(draft.repsMin) || 0,
        reps_max: Number(draft.repsMax) || 0,
        duration_min: draft.durationMin,
        duration_max: draft.durationMax,
      })
      setPage((p) => {
        p.sets.push(data.set)
      })
      // Keep the form open with the same values: adding several identical
      // sets in a row is the common case.
    } catch (err) {
      app.notify(err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Show when={page.loaded} fallback={<PageLoading />}>
      <Show when={!page.error} fallback={<ErrorPanel message={page.error} onRetry={load} />}>
        <PageHeader
          back={`/workout/${params.workout_id}`}
          eyebrow={page.workout.name}
          title={page.exercise.name}
        >
          <IconButton
            icon="edit"
            label="Edit exercise"
            onClick={() => {
              setName(page.exercise.name)
              setUrl(page.exercise.info_url || '')
              setEditing(true)
            }}
          />
        </PageHeader>

        <Show
          when={editing()}
          fallback={
            <div class="mb-4">
              <InstructionsLink url={page.exercise.info_url} favicon={page.exercise.info_url_favicon} />
            </div>
          }
        >
          <form class="card mb-4 flex flex-col gap-4" onSubmit={save}>
            <label class="flex flex-col gap-1">
              <span class="field-label">Name</span>
              <input
                type="text"
                maxlength="255"
                value={name()}
                onInput={(e) => setName(e.currentTarget.value)}
              />
            </label>
            <label class="flex flex-col gap-1">
              <span class="field-label">Instructions link (optional)</span>
              <input
                type="url"
                inputmode="url"
                placeholder="https://..."
                value={url()}
                onInput={(e) => setUrl(e.currentTarget.value)}
              />
            </label>
            <div class="flex gap-4">
              <button type="button" class="flex-1" onClick={() => setEditing(false)}>
                Cancel
              </button>
              <button type="submit" class="button-good flex-1" disabled={saving()}>
                {saving() ? <Spinner small /> : 'Save'}
              </button>
            </div>
          </form>
        </Show>

        <p class="eyebrow px-1">Sets</p>
        <div class="flex flex-col gap-3">
          <For each={page.sets} fallback={<p class="card muted">No sets yet. Add one below.</p>}>
            {(set, index) => (
              <article class="card flex flex-col gap-3">
                <div class="flex items-center justify-between gap-4">
                  <div class="flex items-center gap-4">
                    <span class="set-number">{index() + 1}</span>
                    <Icon name={set.is_duration ? 'timer' : 'fitness_center'} class="muted" />
                    <span class="text-xl font-bold">{setTarget(set)}</span>
                  </div>
                  <div class="flex gap-2">
                    <IconButton
                      icon="content_copy"
                      label="Duplicate set"
                      busy={copying() === set.set_id}
                      onClick={() => copySet(set)}
                    />
                    <IconButton
                      icon="delete"
                      label="Delete set"
                      onClick={() => setConfirmDelete(set.set_id)}
                    />
                  </div>
                </div>
                <Show when={confirmDelete() === set.set_id}>
                  <Confirm
                    message="Delete this set and its logs?"
                    confirmLabel="Delete"
                    onConfirm={() => deleteSet(set)}
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
                <Icon name="add" /> Set
              </button>
            }
          >
            <form class="card flex flex-col gap-4" onSubmit={addSet}>
              <div class="segmented self-start" role="group" aria-label="Set type">
                <button
                  type="button"
                  class={{ active: draft.type === 'reps' }}
                  onClick={() => setDraft((d) => {
                    d.type = 'reps'
                  })}
                >
                  <Icon name="fitness_center" /> Reps
                </button>
                <button
                  type="button"
                  class={{ active: draft.type === 'duration' }}
                  onClick={() => setDraft((d) => {
                    d.type = 'duration'
                  })}
                >
                  <Icon name="timer" /> Duration
                </button>
              </div>

              <Show
                when={draft.type === 'reps'}
                fallback={
                  <div class="flex flex-col gap-4 sm:flex-row">
                    <DurationField
                      label="Minimum time"
                      class="flex-1"
                      value={draft.durationMin}
                      onValue={(v) => setDraft((d) => {
                        d.durationMin = v
                      })}
                    />
                    <DurationField
                      label="Maximum time (optional)"
                      class="flex-1"
                      value={draft.durationMax}
                      onValue={(v) => setDraft((d) => {
                        d.durationMax = v
                      })}
                    />
                  </div>
                }
              >
                <div class="flex gap-4">
                  <NumberField
                    label="Minimum reps"
                    class="flex-1"
                    value={draft.repsMin}
                    onValue={(v) => setDraft((d) => {
                      d.repsMin = v
                    })}
                  />
                  <NumberField
                    label="Maximum reps (optional)"
                    class="flex-1"
                    placeholder="-"
                    value={draft.repsMax}
                    onValue={(v) => setDraft((d) => {
                      d.repsMax = v
                    })}
                  />
                </div>
              </Show>

              <div class="flex gap-4">
                <button
                  type="button"
                  class="flex-1"
                  onClick={() => {
                    setAdding(false)
                    setDraft(() => ({ ...EMPTY_SET }))
                  }}
                >
                  Close
                </button>
                <button type="submit" class="button-good flex-1" disabled={saving()}>
                  {saving() ? <Spinner small /> : 'Add set'}
                </button>
              </div>
            </form>
          </Show>
        </div>
      </Show>
    </Show>
  )
}
