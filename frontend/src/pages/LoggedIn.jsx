import { createEffect, createMemo, Show } from 'solid-js'
import { useNavigate } from '@solidjs/router'
import { useApp } from '../lib/app'
import { PageLoading, TopMenu } from '../components/ui'

/** Layout for every page that needs a logged in user. */
export default function LoggedIn(props) {
  const app = useApp()
  const navigate = useNavigate()

  const mustLogIn = createMemo(() => app.state.ready && !app.state.loggedIn)

  createEffect(
    () => mustLogIn(),
    (redirect) => {
      if (redirect) navigate('/login', { replace: true })
    },
  )

  return (
    <Show when={app.state.ready && app.state.loggedIn} fallback={<PageLoading />}>
      <TopMenu />
      <main class="container">{props.children}</main>
    </Show>
  )
}
