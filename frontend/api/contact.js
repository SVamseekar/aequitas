const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000
const RATE_LIMIT_MAX = 5
const ipHits = new Map()

function asString(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function parseBody(body) {
  if (typeof body === 'string') {
    try {
      return JSON.parse(body)
    } catch {
      return body
    }
  }
  return body
}

function validateContactRequest(body) {
  if (!body || typeof body !== 'object') {
    return { ok: false, error: 'Invalid request body' }
  }

  if (asString(body.website)) {
    return { ok: false, error: 'Submission rejected' }
  }

  const formStartedAt = Number(body.formStartedAt)
  if (formStartedAt && Date.now() - formStartedAt < 2000) {
    return { ok: false, error: 'Please take a moment to complete the form' }
  }

  const name = asString(body.name)
  const email = asString(body.email)
  const message = asString(body.message)

  if (!name) return { ok: false, error: 'Missing required field: name' }
  if (!EMAIL_RE.test(email)) return { ok: false, error: 'Invalid email address' }
  if (!message) return { ok: false, error: 'Missing required field: message' }

  return {
    ok: true,
    data: {
      name,
      email,
      organisation: asString(body.organisation) || undefined,
      message,
    },
  }
}

async function sendContactNotification(payload, meta) {
  const webhookUrl = (process.env.DISCORD_CONTACT_WEBHOOK_URL || '').trim()
  if (!webhookUrl) {
    throw new Error('DISCORD_CONTACT_WEBHOOK_URL is required')
  }

  const embed = {
    title: 'New Aequitas contact form submission',
    color: 0x6366f1,
    fields: [
      { name: 'Name', value: payload.name, inline: true },
      { name: 'Email', value: payload.email, inline: true },
      { name: 'Organisation', value: payload.organisation || '—', inline: true },
      { name: 'Message', value: payload.message.slice(0, 1024) },
      { name: 'Referer', value: meta.referer || '—', inline: true },
      { name: 'IP', value: meta.ip || '—', inline: true },
    ],
    timestamp: meta.submittedAt,
  }

  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ embeds: [embed] }),
  })

  if (!response.ok) {
    throw new Error(`Discord webhook returned ${response.status}`)
  }
}

function getClientIp(req) {
  const forwarded = req.headers['x-forwarded-for']
  if (typeof forwarded === 'string') return forwarded.split(',')[0]?.trim()
  if (Array.isArray(forwarded)) return forwarded[0]
  return req.socket?.remoteAddress
}

function isRateLimited(ip) {
  if (!ip) return false
  const now = Date.now()
  const entry = ipHits.get(ip)
  if (!entry || now > entry.resetAt) {
    ipHits.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS })
    return false
  }
  entry.count += 1
  return entry.count > RATE_LIMIT_MAX
}

export default async function handler(req, res) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    return res.status(204).end()
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const ip = getClientIp(req)
  if (isRateLimited(ip)) {
    return res.status(429).json({ error: 'Too many requests. Please try again later.' })
  }

  const parsed = validateContactRequest(parseBody(req.body))
  if (!parsed.ok) {
    return res.status(400).json({ error: parsed.error })
  }

  try {
    await sendContactNotification(parsed.data, {
      submittedAt: new Date().toISOString(),
      referer: typeof req.headers.referer === 'string' ? req.headers.referer : undefined,
      ip,
    })
    return res.status(200).json({ ok: true })
  } catch (error) {
    console.error('Contact form notification failed:', error)
    return res.status(503).json({
      error: 'Unable to send your message right now. Please email aequitas@souravamseekar.com directly.',
    })
  }
}
