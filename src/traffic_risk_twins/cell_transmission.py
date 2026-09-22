"""Independent conservation model; the graph enclosure does not certify this CTM."""
import numpy as np


def two_cell(vehicles, demand=20, external_queue=0):
    a,b = vehicles
    incoming = min(demand+external_queue,50-a)
    transfer = min(a,20,50-b)
    outgoing = min(b,5)
    return (a+incoming-transfer,b+transfer-outgoing), external_queue+demand-incoming, outgoing


def step(density, external_queue, demand, length, free_speed, wave_speed, jam, capacity, dt):
    density,length,free_speed,wave_speed,jam,capacity = map(np.asarray,(density,length,free_speed,wave_speed,jam,capacity))
    if np.any(dt*np.maximum(free_speed,wave_speed)/length > 1) or np.any(density < 0) or np.any(density > jam):
        raise ValueError('CFL or feasible density condition violated')
    sending = np.minimum(free_speed*density,capacity)
    receiving = np.minimum(wave_speed*(jam-density),capacity)
    offered = external_queue+demand*dt
    incoming = min(offered/dt,receiving[0])
    flows = np.r_[incoming,np.minimum(sending[:-1],receiving[1:]),sending[-1]]
    nxt = density+dt/length*(flows[:-1]-flows[1:])
    return nxt,offered-incoming*dt,flows[-1]*dt
