import { Link } from 'react-router'

export function LandingHero() {
  return <section className='landing-shell public-hero' aria-labelledby='landing-hero-heading'>
    <div><h1 id='landing-hero-heading'>See who the bus<br />leaves behind.</h1><p>Official timetables × official need.<br />Briefings grounded in your country.</p>
      <div className='flex flex-wrap gap-3 mt-7'><Link to='/contact' className='landing-btn-primary'>Work with us</Link><Link to='/briefings' className='landing-btn-secondary'>Read briefings</Link></div>
    </div>
    <figure><Link to='/app/england' aria-label='Open the local England briefing'><img src='/landing/product-overview.png' width='1586' height='992' alt='Aequitas England overview with population coverage, the real in-country score and an interactive regional map' fetchPriority='high' /></Link><figcaption>England local-pack preview · network 1 August 2026. The analytics engine runs locally.</figcaption></figure>
  </section>
}
