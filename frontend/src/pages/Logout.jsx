import { onSettled } from 'solid-js'
import { useNavigate } from '@solidjs/router'
import { useApp } from '../lib/app'
import { PageLoading } from '../components/ui'

export default function Logout() {
  const app = useApp()
  const navigate = useNavigate()

  onSettled(() => {
    app.logout().finally(() => navigate('/login', { replace: true }))
  })

  return <PageLoading message="Logging out..." />
}
