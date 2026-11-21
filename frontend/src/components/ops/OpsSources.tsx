import type { OpsResponse } from '@/api/types'
const visibleFields = ['provider','name','status','ok','n_updates','n_entities','n_with_delay','source','license']
export function OpsSources({ data }: { data: OpsResponse }) {
  return <section className='app-panel'><h2>Stored feed metadata</h2><p>Provider observations from the collector snapshot. Query parameters and credentials are not displayed.</p>
    {data.feeds?.length ? data.feeds.map((feed, index) => {
      const fields = Object.entries(feed).filter(([key,value]) => visibleFields.includes(key) && ['string','number','boolean'].includes(typeof value))
      return <article className='ops-feed' key={index}><h3>Feed {index + 1}</h3><dl>{fields.map(([key,value]) => {
        let text = String(value)
        if (text.startsWith('http')) { try { const url = new URL(text); text = url.origin + url.pathname } catch { text = 'Source URL unavailable' } }
        return <div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{text}</dd></div>
      })}</dl>{!fields.length && <p>No public summary fields stored for this feed.</p>}</article>
    }) : <p>No feed-level metadata stored in this snapshot.</p>}
  </section>
}
