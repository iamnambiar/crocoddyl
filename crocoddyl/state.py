from utils import a2m
import numpy as np
import pinocchio
from scipy.linalg import block_diag



class StateVector:
    '''
    Basic state class in cartesian space, represented by a vector.
    Tangent, integration and difference are straightforward.
    '''
    def __init__(self,nx):
        self.nx = nx
        self.ndx = nx
        
    def zero(self):
        '''Return a zero reference configuration. '''
        return np.zeros([self.nx])
    def rand(self):
        '''Return a random configuration. '''
        return np.random.rand(self.nx)
    def diff(self,x1,x2):
        '''
        Return the tangent vector representing the difference between x1 and x2,
        i.e. dx such that x1 [+] dx = x2.
        '''
        return x2-x1
    def integrate(self,x1,dx):
        '''
        Return x2 = x1 [+] dx.
        Warning: no timestep here, if integrating a velocity v during an interval dt, 
        set dx = v dt .
        '''
        return x1 + dx
    def Jdiff(self,x1,x2,firstsecond='both'):
        assert(firstsecond in ['first', 'second', 'both' ])
        if firstsecond == 'both': return [ self.Jdiff(x1,x2,'first'),
                                           self.Jdiff(x1,x2,'second') ]

        J = np.zeros([self.ndx,self.ndx])
        if firstsecond=='first':
            J[:,:] = -np.eye(self.ndx)
        elif firstsecond=='second':
            J[:,:] = np.eye(self.ndx)
        return J
    def Jintegrate(self,x,vx,firstsecond='both'):
        assert(firstsecond in ['first', 'second', 'both' ])
        if firstsecond == 'both': return [ self.Jintegrate(x,vx,'first'),
                                           self.Jintegrate(x,vx,'second') ]
        return np.eye(self.ndx)



class StateNumDiff:
    '''
    From a norm state class, returns a class able to num diff. 
    '''
    def __init__(self,State):
        self.State = State
        self.nx  = State.nx
        self.ndx = State.ndx
        self.disturbance = 1e-6
    def zero(self): return self.State.zero()
    def rand(self): return self.State.rand()
    def diff(self,x1,x2): return self.State.diff(x1,x2)
    def integrate(self,x,dx): return self.State.integrate(x,dx)
    def Jdiff(self,x1,x2,firstsecond='both'):
        assert(firstsecond in ['first', 'second', 'both' ])
        if firstsecond == 'both': return [ self.Jdiff(x1,x2,'first'),
                                           self.Jdiff(x1,x2,'second') ]
        dx = np.zeros(self.ndx)
        h  = self.disturbance
        J  = np.zeros([self.ndx,self.ndx])
        d0 = self.diff(x1,x2)
        if firstsecond=='first':
            for k in range(self.ndx):
                dx[k]  = h
                J[:,k] = self.diff(self.integrate(x1,dx),x2)-d0
                dx[k]  = 0
        elif firstsecond=='second':
            for k in range(self.ndx):
                dx[k]  = h
                J[:,k] = self.diff(x1,self.integrate(x2,dx))-d0
                dx[k]  = 0
        J /= h
        return J
    def Jintegrate(self,x,vx,firstsecond='both'):
        assert(firstsecond in ['first', 'second', 'both' ])
        if firstsecond == 'both': return [ self.Jintegrate(x,vx,'first'),
                                           self.Jintegrate(x,vx,'second') ]
        dx = np.zeros(self.ndx)
        h  = self.disturbance
        J  = np.zeros([self.ndx,self.ndx])
        d0 = self.integrate(x,vx)
        if firstsecond=='first':
            for k in range(self.ndx):
                dx[k]  = h
                J[:,k] = self.diff(d0,self.integrate(self.integrate(x,dx),vx))
                dx[k]  = 0
        elif firstsecond=='second':
            for k in range(self.ndx):
                dx[k]  = h
                J[:,k] = self.diff(d0,self.integrate(x,vx+dx))
                dx[k]  = 0
        J /= h
        return J



class StatePinocchio:
    def __init__(self,pinocchioModel):
        self.model = pinocchioModel
        self.nx = self.model.nq + self.model.nv
        self.ndx = 2*self.model.nv
    def zero(self):
        q = pinocchio.neutral(self.model)
        v = np.zeros(self.model.nv)
        return np.concatenate([q.flat,v])
    def rand(self):
        q = pinocchio.randomConfiguration(self.model)
        v = np.random.rand(self.model.nv)*2-1
        return np.concatenate([q.flat,v])
    def diff(self,x0,x1):
        nq,nv,nx,ndx = self.model.nq,self.model.nv,self.nx,self.ndx
        assert( x0.shape == ( nx, ) and x1.shape == ( nx, ))
        q0 = x0[:nq]; q1 = x1[:nq]; v0 = x0[-nv:]; v1 = x1[-nv:]
        dq = pinocchio.difference(self.model,a2m(q0),a2m(q1))
        return np.concatenate([dq.flat,v1-v0])
    def integrate(self,x,dx):
        nq,nv,nx,ndx = self.model.nq,self.model.nv,self.nx,self.ndx
        assert( x.shape == ( nx, ) and dx.shape == ( ndx, ))
        q = x[:nq]; v = x[-nv:]; dq = dx[:nv]; dv = dx[-nv:]
        qn = pinocchio.integrate(self.model,a2m(q),a2m(dq))
        return np.concatenate([ qn.flat, v+dv] )
    def Jdiff(self,x1,x2,firstsecond='both'):
        assert(firstsecond in ['first', 'second', 'both' ])
        if firstsecond == 'both': return [ self.Jdiff(x1,x2,'first'),
                                           self.Jdiff(x1,x2,'second') ]
        if firstsecond == 'second':
            dx = self.diff(x1,x2)
            q  = a2m( x1[:self.model.nq])
            dq = a2m( dx[:self.model.nv])
            Jdq = pinocchio.dIntegrate(self.model,q,dq)[1]
            return  block_diag( np.asarray(np.linalg.inv(Jdq)), np.eye(self.model.nv) )
        else:
            dx = self.diff(x2,x1)
            q  = a2m( x2[:self.model.nq])
            dq = a2m( dx[:self.model.nv])
            Jdq = pinocchio.dIntegrate(self.model,q,dq)[1]
            return -block_diag( np.asarray(np.linalg.inv(Jdq)), np.eye(self.model.nv) )
        
    def Jintegrate(self,x,dx,firstsecond='both'):
        assert(firstsecond in ['first', 'second', 'both' ])
        assert(x.shape == ( self.nx, ) and dx.shape == (self.ndx,) )
        if firstsecond == 'both': return [ self.Jintegrate(x,dx,'first'),
                                           self.Jintegrate(x,dx,'second') ]
        q  = a2m( x[:self.model.nq])
        dq = a2m(dx[:self.model.nv])
        Jq,Jdq = pinocchio.dIntegrate(self.model,q,dq)
        if firstsecond=='first':
            # Derivative wrt x
            return block_diag( np.asarray(Jq), np.eye(self.model.nv) )
        else:
            # Derivative wrt v
            return block_diag( np.asarray(Jdq), np.eye(self.model.nv) )