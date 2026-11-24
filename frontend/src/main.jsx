import 'material-icons/iconfont/filled.css'
import './index.css'

import { render } from '@solidjs/web'
import { Router } from './router'
import { AppProvider } from './lib/app'
import { Toasts } from './components/ui'

const root = document.getElementById('root')

render(
  () => (
    <AppProvider>
      <Router>
        {(props) => (
          <>
            {props.children}
            <Toasts />
          </>
        )}
      </Router>
    </AppProvider>
  ),
  root,
)
