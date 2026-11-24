import { createRouter } from '@solidjs/router'

import Landing from './pages/Landing'
import Login from './pages/Login'
import Logout from './pages/Logout'
import Auth from './pages/Auth'
import DeleteAccount from './pages/DeleteAccount'
import LoggedIn from './pages/LoggedIn'
import Account from './pages/Account'
import Workouts from './pages/Workouts'
import Workout from './pages/Workout'
import Exercise from './pages/Exercise'
import WorkoutLogs from './pages/WorkoutLogs'
import Session from './pages/Session'
import NotFound from './pages/NotFound'

export const Router = createRouter({
  routes: [
    { path: '/', component: Landing },
    { path: '/login', component: Login },
    { path: '/logout', component: Logout },
    { path: '/auth/:account_id/:auth_code', component: Auth },
    { path: '/account/delete/:account_id/:auth_code', component: DeleteAccount },
    {
      path: '/',
      component: LoggedIn,
      children: [
        { path: '/account', component: Account },
        { path: '/workouts', component: Workouts },
        { path: '/workout/:workout_id', component: Workout },
        { path: '/workout/:workout_id/logs', component: WorkoutLogs },
        { path: '/workout/:workout_id/exercise/:exercise_id', component: Exercise },
        { path: '/workout/:workout_id/session/:workout_session_id', component: Session },
      ],
    },
    { path: '*404', component: NotFound },
  ],
})
