import { Link, Navigate,useSearchParams } from 'react-router'
import { useAuth } from '@/contexts/AuthContext'
import { Toaster, toast } from 'sonner'
import { Seo } from '@/components/shared/Seo'
import {authReturnPath} from '@/lib/authReturn'

export default function AuthPage() {
  const { user, loading } = useAuth()
  const [params]=useSearchParams(),returnTo=authReturnPath(params.get('returnTo'))
  if (loading) return <div className='app-redesign min-h-screen flex items-center justify-center'><p role='status'>Checking your session…</p></div>
  if (user) return <Navigate to={returnTo} replace />

  const handleGoogle = async () => {
    try {
      const loginPath=`/api/auth/login/google?${new URLSearchParams({returnTo})}`
      const response = await fetch(loginPath, { redirect: 'manual', credentials: 'include' })
      if (response.type === 'opaqueredirect' || response.status === 0 || (response.status >= 300 && response.status < 400)) {
        window.location.href = loginPath
        return
      }
      let detail = 'Google sign-in is not configured'
      try { const body = await response.json(); if (body.detail) detail = body.detail } catch { /* Non-JSON response keeps the existing unavailable message. */ }
      toast.error(detail)
    } catch { toast.error('Google sign-in is not configured') }
  }

  return <><Toaster position='top-right' /><div className='app-redesign auth-layout'>
    <Seo title='Sign In — Aequitas' description='Save findings, policy notes, regions and conversations in your Aequitas workspace.' path='/auth' noindex />
    <aside className='auth-brand'><Link className='app-wordmark' to='/'>Aequitas</Link><Link className='text-sm' to='/briefings'>Back to briefings</Link><p className='auth-brand-note'>Official evidence. In-country ranks.</p></aside>
    <main className='auth-main'><section className='app-panel auth-panel'>
      <h1>Sign in to Aequitas</h1>
      <p className='mt-4 mb-7'>Save findings, policy notes, regions and conversations in your workspace.</p>
      <button type='button' className='app-btn-primary w-full justify-center px-5 py-3.5' onClick={() => void handleGoogle()}>
        <svg width='22' height='22' viewBox='0 0 24 24' aria-hidden='true'><circle cx='12' cy='12' r='11' fill='white' /><path fill='#4285F4' d='M19.8 12.2c0-.5 0-1-.1-1.5H12v3h4.4a3.8 3.8 0 0 1-1.6 2.4v2h2.6c1.6-1.5 2.4-3.5 2.4-5.9Z' /><path fill='#34A853' d='M12 20c2.1 0 3.8-.7 5.1-1.9l-2.6-2c-.7.5-1.6.8-2.5.8-2 0-3.7-1.3-4.3-3.1H5v2.1A8 8 0 0 0 12 20Z' /><path fill='#FBBC05' d='M7.7 13.8a5.4 5.4 0 0 1 0-3.6V8.1H5a8 8 0 0 0 0 7.8l2.7-2.1Z' /><path fill='#EA4335' d='M12 7.1c1.2 0 2.2.4 3 1.2l2.3-2.2A8 8 0 0 0 5 8.1l2.7 2.1A4.5 4.5 0 0 1 12 7.1Z' /></svg>
        Continue with Google
      </button>
      <p className='text-center border-t border-border pt-6 mt-6'>By continuing, you agree to our<br /><Link className='app-text-link' to='/privacy'>Privacy Policy</Link> and <Link className='app-text-link' to='/terms'>Terms of Service</Link>.</p>
      <Link className='app-text-link block text-center border-t border-border pt-6 mt-6' to='/briefings'>Read public briefings</Link>
    </section></main>
  </div></>
}
