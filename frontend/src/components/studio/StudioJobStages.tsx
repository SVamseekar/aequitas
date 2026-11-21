import { operationLabel, type StudioJob, type StudioPatch } from '@/lib/studio'

const stages = [
  ['validated', 'Validate patch', 'Check operations and country bounds'],
  ['baseline', 'Read baseline', 'Load the selected network and population'],
  ['coverage', 'Recalculate coverage', 'Measure the change in walk-to-stop coverage'],
  ['results', 'Build results', 'Prepare the score, map and area results'],
] as const
interface Props {
  job: StudioJob | null; submitted: StudioPatch | null; starting: boolean
  error: string | null; onRetryStatus: () => void; onRetry: () => void
}
export default function StudioJobStages({ job, submitted, starting, error, onRetryStatus, onRetry }: Props) {
  const active = stages.findIndex(([stage]) => stage === job?.stage)
  return <div className='studio-two-columns studio-job-layout'>
    <section className='app-panel'>
      <h2>Calculation stages</h2>
      {!job && !starting ? <p className='studio-notice mt-4'>No calculation has started. Review your draft, then apply the patch.</p> : null}
      <ol className='studio-stages' aria-live='polite'>
        {stages.map(([stage, title, description], index) => {
          const complete = job?.status === 'done' || (active > index) || (stage === 'validated' && Boolean(job))
          const inProgress = job?.status === 'running' && active === index && !complete
          const failed = job?.status === 'error' && active === index
          const status = complete ? 'Complete' : failed ? 'Failed' : inProgress ? 'In progress' : index === 0 && starting ? 'Submitting' : 'Not started'
          return <li key={stage} className={`studio-stage ${complete ? 'complete' : inProgress ? 'active' : ''}`}>
            <span className='studio-stage-index' aria-hidden='true'>{complete ? '✓' : index + 1}</span>
            <div><h3>{index + 1}. {title}</h3><p>{description}</p></div>
            <span className='studio-stage-status'>{status}</span>
          </li>
        })}
      </ol>
      {error ? <div role='alert' className='studio-notice'><p>{error}</p><button type='button' className='app-panel-button mt-3' onClick={job && job.status !== 'error' ? onRetryStatus : onRetry}>{job && job.status !== 'error' ? 'Retry status check' : 'Retry calculation'}</button></div> : null}
      <p>Stage labels follow the worker. Retrying a failed calculation creates a new run from the submitted patch.</p>
    </section>
    <aside className='app-panel'><h2>Submitted operations</h2>
      {submitted ? <><dl className='studio-review'><div><dt>Country</dt><dd>{submitted.country}</dd></div><div><dt>Region</dt><dd>{submitted.region}</dd></div><div><dt>Area</dt><dd>{submitted.urban_rural}</dd></div><div><dt>Network</dt><dd>Current warehouse</dd></div><div><dt>Method</dt><dd>Walk-to-stop · 400 m</dd></div></dl><ol className='studio-operation-list'>{submitted.ops.map((op, index) => <li key={index}>{operationLabel(op)}</li>)}</ol></> : <p className='studio-empty'>The submitted context will appear here. Draft changes cannot alter a running calculation.</p>}
    </aside>
  </div>
}
