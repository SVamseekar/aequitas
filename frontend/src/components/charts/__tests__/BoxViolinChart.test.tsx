import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import BoxViolinChart from '../BoxViolinChart'

describe('Stored route distributions',()=>{
  it('preserves zero minima and plots only supplied finite outliers without inventing a density',()=>{
    render(<BoxViolinChart chartData={{unit:'km',groups:[{label:'Actual region',min:0,q1:5,median:10,q3:15,max:40,outliers:[40,null]}]}} />)
    const plot=screen.getByRole('img')
    expect(plot).toHaveTextContent('km')
    expect(plot.querySelectorAll('[aria-label="dot"] circle')).toHaveLength(1)
    expect(screen.getByText(/No density curve is inferred/)).toBeInTheDocument()
  })
  it('keeps missing and invalid quartiles unavailable',()=>{
    render(<BoxViolinChart chartData={{groups:[{label:'Missing',min:0,q1:null,median:10,q3:15,max:40},{label:'Invalid',min:0,q1:20,median:10,q3:15,max:40}]}} />)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText('No complete distribution observations are available.')).toBeInTheDocument()
  })
})
