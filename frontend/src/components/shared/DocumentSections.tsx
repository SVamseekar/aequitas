export interface DocumentSection { title: string; body: string }
const sectionId = (title: string) => title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

/** Reading layout for existing policy copy; content remains owned by each page. */
export function DocumentSections({ sections }: { sections: readonly DocumentSection[] }) {
  return <div className='public-document-layout'>
    <nav aria-label='On this page' className='public-document-nav'><h2>On this page</h2>{sections.map(section => <a key={section.title} href={`#${sectionId(section.title)}`}>{section.title}</a>)}</nav>
    <div className='public-document-content'>{sections.map(section => <section id={sectionId(section.title)} key={section.title} tabIndex={-1}><h2>{section.title}</h2><p>{section.body}</p></section>)}</div>
  </div>
}
