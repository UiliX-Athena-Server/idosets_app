import { createSignal } from 'solid-js'
import { useApp } from '../lib/app'
import { Icon } from './ui'

export default function ThemeToggle() {
  const app = useApp()
  const [busy, setBusy] = createSignal(false)

  async function toggle() {
    const theme = app.state.theme === 'dark' ? 'light' : 'dark'
    setBusy(true)
    // Switch immediately; the save just makes it stick.
    document.documentElement.dataset.theme = theme
    try {
      await app.saveSettings({ theme })
    } catch (err) {
      document.documentElement.dataset.theme = app.state.theme
      app.notify(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      class="icon-button"
      disabled={busy()}
      title="Switch theme"
      aria-label="Switch theme"
      onClick={toggle}
    >
      <Icon name={app.state.theme === 'dark' ? 'light_mode' : 'dark_mode'} />
    </button>
  )
}
