import { Show } from 'solid-js'
import { Icon } from './ui'

/**
 * Shown when notifyvia.email's rate limiter refuses to send any more emails
 * (5 a day).
 */
export default function EmailLimitNotice(props) {
  return (
    <Show when={props.message}>
      <div class="notice notice-warning" role="alert">
        <Icon name="mark_email_unread" />
        <div>
          <p class="font-bold">Daily email limit reached</p>
          <p>{props.message}</p>
        </div>
      </div>
    </Show>
  )
}
