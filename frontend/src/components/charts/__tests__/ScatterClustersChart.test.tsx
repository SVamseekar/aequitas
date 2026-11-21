import { render,screen } from '@testing-library/react'
import { describe,expect,it } from 'vitest'
import ScatterClustersChart from '../ScatterClustersChart'

describe('Stored cluster identities',()=>{
  it('uses source IDs to resolve descriptive labels and colors, retaining zero coordinates',()=>{
    render(<ScatterClustersChart chartData={{clusters:[{id:6,label:'Medium-length cross-boundary routes averaging 26.2 km',colour:'#9fda3a',n:1051}],data:[{id:'actual-route',cluster:6,x:0,y:10},{cluster:6,x:null,y:20}],x_label:'Route length (km)',y_label:'Stops'}} />)
    const plot=screen.getByRole('img')
    expect(plot).toHaveTextContent('6 · Medium-length cross-boundary')
    expect(plot.querySelectorAll('[aria-label="dot"] circle')).toHaveLength(1)
    expect(plot.querySelector('[aria-label="dot"] circle')).toHaveAttribute('fill','#9fda3a')
  })
  it('does not infer point positions or a small sample from cluster counts',()=>{
    render(<ScatterClustersChart chartData={{cluster_sizes:[{label:'Actual group',n:5000}]}} />)
    expect(screen.queryByRole('img',{name:'Cluster scatter'})).toBeNull()
    expect(screen.getByRole('img',{name:'Cluster sizes'})).toHaveTextContent('5,000')
    expect(screen.getByText(/No scatter positions are inferred/)).toBeInTheDocument()
    expect(screen.queryByText(/Too few/)).toBeNull()
  })
  it('keeps source identities, zero counts and missing positions in compact route layout',()=>{
    render(<ScatterClustersChart chartData={{compact_layout:true,cluster_entity:'routes',
      clusters:[{id:0,label:'Actual empty group',colour:'#123456'},{id:6,label:'Actual route group',colour:'#abcdef'}],
      cluster_sizes:[{label:'Actual empty group',n:0},{label:'Actual route group',n:27}],
      data:[{id:'route-zero',cluster:6,x:0,y:0},{id:'missing',cluster:6,x:null,y:20}],
    }} />)
    expect(screen.getByLabelText('Stored cluster legend')).toHaveTextContent('Cluster 0')
    expect(screen.getByLabelText('Stored cluster legend')).toHaveTextContent('Cluster 6')
    expect(screen.getByRole('img',{name:'Cluster scatter'}).querySelectorAll('[aria-label="dot"] circle')).toHaveLength(1)
    expect(screen.getByRole('img',{name:'Cluster sizes'})).toHaveTextContent('C0')
    expect(screen.getByRole('table',{name:'Stored cluster counts',hidden:true})).toHaveTextContent('27')
  })
})
