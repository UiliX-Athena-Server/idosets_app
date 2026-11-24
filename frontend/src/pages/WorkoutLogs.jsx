import { createStore, For, onSettled, Show } from 'solid-js'
import { useParams } from '@solidjs/router'
import { api } from '../lib/api'
import { formatDuration, formatNumber, unitLabel } from '../lib/format'
import { ErrorPanel, InstructionsLink, PageHeader, PageLoading } from '../components/ui'
import LineChart from '../components/LineChart'

/** Turn a list of logs into the series worth charting. */
function series(logs, units) {
  const labels = logs.map((_, i) => `Set ${i + 1}`)
  const pick = (key) => logs.map((log) => log[key] || 0)
  const charts = []
  if (logs.some((l) => l.reps > 0)) {
    charts.push({ title: 'Reps', values: pick('reps'), color: '#c04bc0', whole: true, format: (v) => `${formatNumber(v)} reps` })
  }
  if (logs.some((l) => l.duration > 0)) {
    charts.push({ title: 'Duration', values: pick('duration'), color: '#8c00ff', whole: true, format: formatDuration })
  }
  if (logs.some((l) => l.weight > 0)) {
    charts.push({
      title: `Weight (${unitLabel(units)})`,
      values: pick('weight'),
      color: '#4bc0c0',
      format: (v) => `${formatNumber(v)} ${unitLabel(units)}`,
    })
  }
  return charts.map((c) => ({ ...c, labels }))
}

export default function WorkoutLogs() {
  const params = useParams()
  const [page, setPage] = createStore({ loaded: false, error: '', workout: null, exercises: [], units: 'kgs' })

  async function load() {
    try {
      const data = await api.get(`/workouts/${params.workout_id}/logs?limit=30`)
      setPage((p) => {
        p.workout = data.workout
        p.exercises = data.exercises
        p.units = data.units
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

  return (
    <Show when={page.loaded} fallback={<PageLoading />}>
      <Show when={!page.error} fallback={<ErrorPanel message={page.error} onRetry={load} />}>
        <PageHeader back="/workouts" eyebrow="Progress" title={page.workout.name} />
        <p class="muted mb-4 text-sm">Your last 30 logged sets of each exercise.</p>
        <div class="flex flex-col gap-4">
          <For each={page.exercises} fallback={<p class="card muted">This workout has no exercises yet.</p>}>
            {(exercise) => (
              <article class="card flex flex-col gap-4">
                <div>
                  <h2 class="text-2xl font-bold">{exercise.name}</h2>
                  <InstructionsLink url={exercise.info_url} favicon={exercise.info_url_favicon} />
                </div>
                <Show
                  when={exercise.logs.length > 0}
                  fallback={<p class="muted">Nothing logged yet. Finish a workout to see progress here.</p>}
                >
                  <div class="grid gap-4 md:grid-cols-2">
                    <For each={series(exercise.logs, page.units)}>
                      {(chart) => (
                        <LineChart
                          title={chart.title}
                          labels={chart.labels}
                          values={chart.values}
                          color={chart.color}
                          format={chart.format}
                          whole={chart.whole}
                        />
                      )}
                    </For>
                  </div>
                </Show>
              </article>
            )}
          </For>
        </div>
      </Show>
    </Show>
  )
}
