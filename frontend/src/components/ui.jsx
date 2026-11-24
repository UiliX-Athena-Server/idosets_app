import { createSignal, For, Show } from 'solid-js'
import { useNavigate } from '@solidjs/router'
import { useApp } from '../lib/app'
import { sanitiseDecimal, sanitiseWhole } from '../lib/format'

export function Icon(props) {
  return (
    <span class={['material-icons', props.class]} aria-hidden="true">
      {props.name}
    </span>
  )
}

/** A round icon button. */
export function IconButton(props) {
  return (
    <button
      type="button"
      class={['icon-button', props.class, { 'is-busy': !!props.busy }]}
      title={props.label}
      aria-label={props.label}
      disabled={props.disabled || props.busy}
      onClick={(e) => props.onClick?.(e)}
    >
      <Show when={props.busy} fallback={<Icon name={props.icon} />}>
        <Spinner small />
      </Show>
    </button>
  )
}

export function Spinner(props) {
  return (
    <svg
      class={['spinner', { 'spinner-small': !!props.small }]}
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      role="status"
      aria-label="Loading"
    >
      <circle cx="12" cy="12" r="9.5" fill="none" stroke-width="3" />
    </svg>
  )
}

export function PageLoading(props) {
  return (
    <div class="page-loading">
      <Spinner />
      <Show when={props.message}>
        <p>{props.message}</p>
      </Show>
    </div>
  )
}

export function ErrorPanel(props) {
  return (
    <div class="card card-warning flex flex-col items-center gap-4 text-center">
      <p>{props.message}</p>
      <Show when={props.onRetry}>
        <button type="button" onClick={() => props.onRetry()}>
          Try again
        </button>
      </Show>
    </div>
  )
}

export function Toasts() {
  const app = useApp()
  return (
    <div class="toasts" aria-live="polite">
      <For each={app.state.toasts}>
        {(toast) => (
          <div class={['toast', `toast-${toast.kind}`]} role="status">
            <Icon
              name={
                { success: 'check_circle', warning: 'warning', error: 'error' }[toast.kind] ||
                'info'
              }
            />
            <p class="flex-1">{toast.message}</p>
            <button
              type="button"
              class="toast-close"
              aria-label="Dismiss"
              onClick={() => app.dismiss(toast.id)}
            >
              <Icon name="close" />
            </button>
          </div>
        )}
      </For>
    </div>
  )
}

export function TopMenu() {
  const app = useApp()
  const navigate = useNavigate()

  async function logout() {
    await app.logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav class="top-menu">
      <a href="/workouts" class="brand">
        💪 I Do Sets
      </a>
      <div class="flex gap-2">
        <a href="/workouts" class="nav-link" title="Workouts">
          <Icon name="fitness_center" />
          <span class="nav-label">Workouts</span>
        </a>
        <a href="/account" class="nav-link" title="Account">
          <Icon name="person" />
          <span class="nav-label">Account</span>
        </a>
        <button type="button" class="nav-link" title="Log out" onClick={logout}>
          <Icon name="logout" />
          <span class="nav-label">Log out</span>
        </button>
      </div>
    </nav>
  )
}

/** Back button + title row used at the top of pages. */
export function PageHeader(props) {
  return (
    <div class="page-header">
      <Show when={props.back}>
        <a href={props.back} class="icon-button" aria-label="Back" title="Back">
          <Icon name="arrow_back" />
        </a>
      </Show>
      <div class="min-w-0 flex-1">
        <Show when={props.eyebrow}>
          <p class="eyebrow">{props.eyebrow}</p>
        </Show>
        <h1 class="page-title">{props.title}</h1>
      </div>
      {props.children}
    </div>
  )
}

/**
 * Inline "are you sure?" row. Shown in place of a destructive action.
 */
export function Confirm(props) {
  const [busy, setBusy] = createSignal(false)

  async function confirm() {
    setBusy(true)
    try {
      await props.onConfirm()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div class="confirm">
      <p>{props.message}</p>
      <div class="flex gap-2">
        <button
          type="button"
          class={props.danger === false ? 'button-good' : 'button-bad'}
          disabled={busy()}
          onClick={confirm}
        >
          <Show when={busy()} fallback={props.confirmLabel || 'Yes'}>
            <Spinner small />
          </Show>
        </button>
        <button type="button" disabled={busy()} onClick={() => props.onCancel()}>
          {props.cancelLabel || 'No'}
        </button>
      </div>
    </div>
  )
}

/**
 * A text box that only accepts numbers. `decimal` allows a decimal point
 * (weights); otherwise whole numbers only (reps, seconds).
 * Controlled through `value` (string) + `onValue(string)`.
 */
export function NumberField(props) {
  const sanitise = (text) => (props.decimal ? sanitiseDecimal(text) : sanitiseWhole(text))

  return (
    <label class={['number-field', props.class]}>
      <span class="field-label">{props.label}</span>
      <span class="field-box">
        <input
          type="text"
          inputmode={props.decimal ? 'decimal' : 'numeric'}
          autocomplete="off"
          enterkeyhint={props.enterkeyhint || 'done'}
          placeholder={props.placeholder ?? '0'}
          value={props.value}
          ref={(el) => props.ref?.(el)}
          onFocus={(e) => e.currentTarget.select()}
          onInput={(e) => {
            const next = sanitise(e.currentTarget.value)
            e.currentTarget.value = next
            props.onValue(next)
          }}
        />
        <Show when={props.suffix}>
          <span class="field-suffix">{props.suffix}</span>
        </Show>
      </span>
    </label>
  )
}

/**
 * Minutes + seconds number boxes. Value is total seconds (number).
 */
export function DurationField(props) {
  const minutes = () => (props.value ? String(Math.floor(props.value / 60)) : '')
  const seconds = () => (props.value ? String(props.value % 60) : '')

  function update(mins, secs) {
    props.onValue((Number(mins) || 0) * 60 + (Number(secs) || 0))
  }

  return (
    <div class={['duration-field', props.class]}>
      <span class="field-label">{props.label}</span>
      <div class="flex gap-2">
        <NumberField
          label="mins"
          value={minutes()}
          ref={props.ref}
          onValue={(mins) => update(mins, seconds())}
        />
        <NumberField
          label="secs"
          value={seconds()}
          onValue={(secs) => update(minutes(), secs)}
        />
      </div>
    </div>
  )
}

export function InstructionsLink(props) {
  return (
    <Show when={props.url}>
      <a
        href={props.url}
        target="_blank"
        rel="noopener noreferrer"
        referrerpolicy="no-referrer"
        class="instructions-link"
      >
        <Show when={props.favicon} fallback={<Icon name="link" />}>
          <img
            src={props.favicon}
            alt=""
            class="favicon"
            referrerpolicy="no-referrer"
            onError={(e) => (e.currentTarget.style.display = 'none')}
          />
        </Show>
        <span class="underline">Instructions</span>
        <Icon name="open_in_new" class="text-base" />
      </a>
    </Show>
  )
}
