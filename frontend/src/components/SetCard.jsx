import { createSignal, createStore, Show } from 'solid-js'
import { formatDuration, formatNumber, setTarget, unitLabel } from '../lib/format'
import { Confirm, DurationField, Icon, IconButton, NumberField } from './ui'

/** "10 reps · 62.5 kg" style summary of a log. */
export function describeLog(log, set, units) {
  if (!log) return ''
  const parts = []
  if (set.is_reps || log.reps > 0) parts.push(`${log.reps || 0} reps`)
  if (set.is_duration || log.duration > 0) parts.push(formatDuration(log.duration))
  if (log.weight > 0) parts.push(`${formatNumber(log.weight)} ${unitLabel(units)}`)
  return parts.join(' · ')
}

/**
 * One set while doing a workout.
 *
 * props: set, index, units, open, finished, copying,
 *        onOpen(), onClose(), onLog(values), onUndo(), onCopy()
 */
export default function SetCard(props) {
  const [draft, setDraft] = createStore({ reps: '', weight: '', duration: 0 })
  const [confirmUndo, setConfirmUndo] = createSignal(false)
  let firstInput

  function fill(log) {
    setDraft((d) => {
      d.reps = log?.reps ? String(log.reps) : ''
      d.weight = log?.weight ? formatNumber(log.weight) : ''
      d.duration = log?.duration || 0
    })
  }

  function open() {
    // Editing an existing log starts from its values; otherwise start empty
    // and show last time's numbers as hints.
    fill(props.set.set_log)
    props.onOpen()
    setTimeout(() => firstInput?.focus(), 50)
  }

  function submit(e) {
    e.preventDefault()
    props.onLog({
      reps: Number(draft.reps) || 0,
      weight: Number(draft.weight) || 0,
      duration: draft.duration || 0,
    })
  }

  const previous = () => props.set.previous_log
  const done = () => !!props.set.set_log

  return (
    <article
      id={`set-${props.set.set_id}`}
      class={['set-card', { 'is-done': done(), 'is-open': props.open }]}
    >
      <div class="flex items-center justify-between gap-3">
        <div class="flex min-w-0 items-center gap-3">
          <span class="set-number">{props.index + 1}</span>
          <div class="min-w-0">
            <p class="flex items-center gap-1 text-lg font-bold">
              <Icon name={props.set.is_duration ? 'timer' : 'fitness_center'} class="muted text-xl" />
              {setTarget(props.set)}
            </p>
            <Show when={previous()}>
              <p class="previous-log" title={`Last time: ${previous().finished_display}`}>
                <Icon name="history" class="text-base" />
                Last time: {describeLog(previous(), props.set, props.units)}
                <span class="muted"> ({previous().finished_display})</span>
              </p>
            </Show>
          </div>
        </div>

        <div class="flex shrink-0 gap-2">
          <Show when={!props.finished}>
            <IconButton
              icon="content_copy"
              label="Add another set like this"
              busy={props.copying}
              onClick={() => props.onCopy()}
            />
            <Show
              when={done()}
              fallback={
                <IconButton icon="done" label="Log this set" class="icon-button-good" onClick={open} />
              }
            >
              <IconButton icon="undo" label="Undo this set" onClick={() => setConfirmUndo(true)} />
            </Show>
          </Show>
        </div>
      </div>

      <Show when={done() && !props.open}>
        <button
          type="button"
          class="set-log"
          disabled={props.finished}
          title={props.finished ? '' : 'Edit this log'}
          onClick={open}
        >
          <Icon name="check_circle" />
          <span>{describeLog(props.set.set_log, props.set, props.units)}</span>
          <Show when={props.set.set_log.pending}>
            <span class="pending-badge" title="Saved on this device, will sync when online">
              <Icon name="cloud_off" class="text-base" /> not synced
            </span>
          </Show>
        </button>
      </Show>

      <Show when={confirmUndo()}>
        <Confirm
          message="Undo this set?"
          confirmLabel="Undo"
          onConfirm={async () => {
            await props.onUndo()
            setConfirmUndo(false)
          }}
          onCancel={() => setConfirmUndo(false)}
        />
      </Show>

      <Show when={props.open}>
        <form class="log-form" onSubmit={submit}>
          <div class="flex flex-wrap gap-3">
            <Show when={props.set.is_reps}>
              <NumberField
                label="Reps"
                class="flex-1"
                ref={(el) => (firstInput = el)}
                enterkeyhint="next"
                placeholder={previous()?.reps ? String(previous().reps) : '0'}
                value={draft.reps}
                onValue={(v) => setDraft((d) => {
                  d.reps = v
                })}
              />
            </Show>
            <NumberField
              label="Weight"
              class="flex-1"
              decimal
              suffix={unitLabel(props.units)}
              ref={(el) => {
                if (!props.set.is_reps && !props.set.is_duration) firstInput = el
              }}
              placeholder={previous()?.weight ? formatNumber(previous().weight) : '0'}
              value={draft.weight}
              onValue={(v) => setDraft((d) => {
                d.weight = v
              })}
            />
          </div>
          <Show when={props.set.is_duration}>
            <DurationField
              label="Time"
              ref={(el) => (firstInput = el)}
              value={draft.duration}
              onValue={(v) => setDraft((d) => {
                d.duration = v
              })}
            />
          </Show>

          <Show when={previous()}>
            <button type="button" class="link-button self-start" onClick={() => fill(previous())}>
              <Icon name="history" class="text-base" /> Use last time's numbers
            </button>
          </Show>

          <div class="flex gap-3">
            <button type="button" class="flex-1" onClick={() => props.onClose()}>
              Cancel
            </button>
            <button type="submit" class="button-good flex-1">
              Save set
            </button>
          </div>
        </form>
      </Show>
    </article>
  )
}
