import { Show } from 'solid-js'
import { useApp } from '../lib/app'
import ThemeToggle from '../components/ThemeToggle'
import Footer from '../components/Footer'

import screenshotLarge from '../assets/screenshot-large.png'
import screenshotHome from '../assets/screenshot-home.png'
import screenshotLogs from '../assets/screenshot-logs.png'

export default function Landing() {
  const app = useApp()

  return (
    <>
      <main class="container">
        <div class="flex flex-col items-center gap-6 py-10 text-center">
          <h1 class="text-4xl font-bold">💪 I Do Sets</h1>
          <p>A workout app focused on doing sets.</p>
          <Show
            when={app.state.loggedIn}
            fallback={
              <a class="button button-good button-large" href="/login">
                Log in / Sign up
              </a>
            }
          >
            <a class="button button-good button-large" href="/workouts">
              Go to your workouts
            </a>
          </Show>
          <ThemeToggle />
        </div>

        <img
          src={screenshotLarge}
          class="mb-4 w-full rounded-lg shadow-2xl"
          alt="Screenshot of setting a workout"
        />
        <div class="landing-screenshots">
          <img src={screenshotHome} class="rounded-lg shadow-2xl" alt="Screenshot of the workouts page" />
          <img src={screenshotLogs} class="rounded-lg shadow-2xl" alt="Screenshot of workout logs" />
        </div>

        <Footer />

        <section class="legal">
          <h2 class="text-center">The boring stuff...</h2>
          <h3>Privacy Policy</h3>
          <p>This app stores the following personal information:</p>
          <ul>
            <li>Email Address</li>
            <li>Workout Data</li>
          </ul>
          <p>
            This data is stored in a secure database and is not, and will never be shared with any
            third party.
          </p>
          <p>
            To delete your account, log in, then go to Account, then Delete Account. Your email
            address, workouts, and workout logs will be completely deleted. There is no way of
            reversing this.
          </p>
          <h3>Cookie Policy</h3>
          <p>
            This app uses cookies to store your login session data. The following values are stored
            on your computer in order for this website to work:
          </p>
          <ul>
            <li>[authentication markers]</li>
            <li>theme</li>
            <li>units</li>
          </ul>
          <p>
            This website does not directly use third party cookies. However, when storing a workout
            instruction link, the system will find the favicon of the website entered. Loading that
            icon may let the other website attempt to set third party cookies on your computer.
          </p>
          <h3>Terms and Conditions</h3>
          <p>By using this website, you agree to the following:</p>
          <ul>
            <li>You will not use this website for any illegal activity</li>
            <li>You will not attempt to use this website to harm others</li>
          </ul>
          <p>
            This site is under the jurisdiction of the United Kingdom, by using this site you agree to
            settle any legal matters within the United Kingdom.
          </p>
          <p>
            This site does not address persons under the age of 13; You are not to use this site if
            you are under this age. If you are the parent or guardian of an account found to be on
            this site which has been made by a person of this age please log in to the account, go
            to Account, then Delete Account.
          </p>
        </section>
      </main>
    </>
  )
}
